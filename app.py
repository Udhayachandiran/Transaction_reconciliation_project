from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
from reconciliation import ReconciliationProcessor

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    # Check if files are present
    if 'statement_file' not in request.files or 'settlement_file' not in request.files:
        return redirect(request.url)
    
    statement_file = request.files['statement_file']
    settlement_file = request.files['settlement_file']
    
    # Check if files are selected
    if statement_file.filename == '' or settlement_file.filename == '':
        return redirect(request.url)
    
    # Validate and save files
    if statement_file and allowed_file(statement_file.filename) and \
       settlement_file and allowed_file(settlement_file.filename):
        
        statement_filename = secure_filename(statement_file.filename)
        settlement_filename = secure_filename(settlement_file.filename)
        
        statement_path = os.path.join(app.config['UPLOAD_FOLDER'], statement_filename)
        settlement_path = os.path.join(app.config['UPLOAD_FOLDER'], settlement_filename)
        
        statement_file.save(statement_path)
        settlement_file.save(settlement_path)
        
        # Process reconciliation
        try:
            processor = ReconciliationProcessor(statement_path, settlement_path)
            results = processor.run()
            
            # Convert DataFrames to HTML tables
            results_html = {
                'present_in_both_statement': results['present_in_both_statement'].to_html(classes='table table-striped', index=False),
                'present_in_both_settlement': results['present_in_both_settlement'].to_html(classes='table table-striped', index=False),
                'present_in_settlement_only': results['present_in_settlement_only'].to_html(classes='table table-striped', index=False),
                'present_in_statement_only': results['present_in_statement_only'].to_html(classes='table table-striped', index=False),
                'amount_comparison': results['amount_comparison'].to_html(classes='table table-striped', index=False),
                'variance': results['variance'].to_html(classes='table table-striped', index=False),
                'counts': {
                    'both_statement': len(results['present_in_both_statement']),
                    'both_settlement': len(results['present_in_both_settlement']),
                    'settlement_only': len(results['present_in_settlement_only']),
                    'statement_only': len(results['present_in_statement_only']),
                    'variance': len(results['variance'])
                }
            }
            
            return render_template('results.html', results=results_html)
            
        except Exception as e:
            return f"Error processing files: {str(e)}"
    
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
