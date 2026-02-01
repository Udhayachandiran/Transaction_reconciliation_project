# Transaction Reconciliation System

A Flask-based web application for reconciling financial transactions between Statement and Settlement files.

## Problem Statement

This application processes two Excel files (Statement and Settlement) to:
1. Extract and clean transaction data
2. Tag transactions for reconciliation based on business rules
3. Match transactions between files using Partner PIN
4. Identify variances and discrepancies
5. Compare settlement amounts

## Features

- **File Upload Interface**: Simple web interface to upload Statement and Settlement Excel files
- **Automated Processing**: Handles data cleaning, extraction, and reconciliation logic
- **Categorized Results**: Displays transactions in 3 categories:
  - Present in Both files
  - Present in Settlement only
  - Present in Statement only (Variance)
- **Amount Comparison**: Side-by-side comparison of settlement amounts with calculated differences

## Tech Stack

- Python 3.10
- Flask 2.3.0
- Pandas 2.0.0
- Bootstrap 5.1.3

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/reconciliation-project.git
cd reconciliation-project
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Flask application:
```bash
python app.py
```

2. Open browser and navigate to `http://localhost:5000`

3. Upload Statement and Settlement Excel files

4. View reconciliation results

## Project Structure
```
reconciliation-project/
├── app.py                  # Flask application
├── reconciliation.py       # Core reconciliation logic
├── templates/
│   ├── upload.html        # File upload interface
│   └── results.html       # Results display
├── uploads/               # Temporary file storage
├── requirements.txt       # Python dependencies
└── README.md
```

## Reconciliation Logic

### Statement File Processing
1. Delete header rows (1-9, 11)
2. Extract 9-digit Partner PIN from descriptions
3. Tag duplicates with "Cancel" type as "Should Reconcile"
4. Tag "Dollar Received" as "Should Not Reconcile"
5. Tag non-duplicates as "Should Reconcile"

### Settlement File Processing
1. Delete header rows (1-2)
2. Calculate Amount (USD) = PayoutRoundAmt ÷ APIRate
3. Tag duplicates with "Post-Cancel" status as "Should Reconcile"
4. Tag non-duplicates as "Should Reconcile"

### Matching Logic
- Match transactions using Partner PIN
- Categorize into: Present in Both, Settlement Only, Statement Only
- Compare amounts for matched transactions
- Identify variance (transactions in Settlement but not in Statement)

## Implementation Notes

- Used Pin Number column instead of Partner Pin column in Settlement file as it matches extracted PINs
- Post-Cancel is treated as the cancel type in Settlement file
- Only first occurrence of duplicate groups without cancel types is tagged

## Author

Udhayachandiran S B
- Email: udhayachandiransb@gmail.com
- LinkedIn: [linkedin.com/in/udhayachandiran](https://linkedin.com/in/udhayachandiran)
- GitHub: [github.com/Udhayachandiran](https://github.com/Udhayachandiran)