import pandas as pd
import numpy as np
import re

class ReconciliationProcessor:
    def __init__(self, statement_file_path, settlement_file_path):
        self.statement_file = statement_file_path
        self.settlement_file = settlement_file_path
        self.clean_statement_df = None
        self.settlement_df = None
        

    def process_statement_file(self):
        """Process Statement file - Steps 3a to 3e"""
        # Step 3a: Delete rows 1-9 and 11
        statement_df = pd.read_excel(self.statement_file, skiprows=9, header=0)
        statement_df = statement_df.iloc[1:].reset_index(drop=True)
        
        # Remove total row
        stmt_total_row_index = statement_df[
            statement_df['Date'].isna() & 
            statement_df['PQsTrOptOons'].astype(str).str.lower().str.contains('tot')
        ].index[0]
        
        clean_statement_df = statement_df.iloc[:stmt_total_row_index].reset_index(drop=True)
        
        #3b.	From Col D (Descriptions), extract the partner pin (9 digit number at the very end)
        clean_statement_df['Partner_Pin'] = clean_statement_df['PQsTrOptOons'].astype(str).str.strip().str.extract(r'(\d{9})$')
        
        # Clean Type column
        clean_statement_df['Type'] = clean_statement_df['Type'].astype(str).str.strip()
        
        # Step 3c: Identify duplicates
        clean_statement_df['is_duplicate_pin'] = clean_statement_df['Partner_Pin'].duplicated(keep=False)

        #cancel dupl filter
        reconcile_tag_filt = ((clean_statement_df["is_duplicate_pin"]) & 
                      (clean_statement_df['Type'].astype(str).str.strip().str.lower()=='cancel'))
        
        #create Reconcile tag for cancel
        clean_statement_df["Reconcile_Tag"] = np.where(reconcile_tag_filt, "Should Reconcile", None )
        
        # Step 3d: Tag Dollar Received as Should not Reconcile
        dollar_received_filt = (clean_statement_df['Type'].str.strip().str.lower() == 'dollar received')
        clean_statement_df.loc[dollar_received_filt, 'Reconcile_Tag'] = "Should Not Reconcile"
        
        # Step 3e: Tag non-duplicates as Should Reconcile
        non_dup_filt = (~clean_statement_df["is_duplicate_pin"]) & (~dollar_received_filt)
        clean_statement_df.loc[non_dup_filt, 'Reconcile_Tag'] = "Should Reconcile"
        
        self.clean_statement_df = clean_statement_df
        

    def process_settlement_file(self):
        """Process Settlement file - Steps 4a to 4d"""
        # Step 4a: Delete rows 1 and 2
        settlement_df = pd.read_excel(self.settlement_file, skiprows=[0, 1], header=0)
        
        #cleaning and removing the total row
        settlement_df = settlement_df[(settlement_df['PostDate'].notna()) &
                                    (settlement_df['PostDate'].astype(str).str.strip() != '') &
                                    (settlement_df['Pin Number'].notna()) &
                                    (settlement_df['Pin Number'].astype(str).str.strip() != '')].reset_index(drop=True)

        #standardize status
        settlement_df['Status'] = settlement_df['Status'].astype(str).str.strip().str.lower()

        #standardize amounts
        settlement_df['PayoutRoundAmt'] = settlement_df['PayoutRoundAmt'].astype(str).str.replace(',','')
        settlement_df['PayoutRoundAmt'] = pd.to_numeric(settlement_df['PayoutRoundAmt'], errors='coerce')

        settlement_df['APIRATE'] = settlement_df['APIRATE'].astype(str).str.replace(',','')
        settlement_df['APIRATE'] = pd.to_numeric(settlement_df['APIRATE'], errors='coerce')
        
        # Step 4b: Calculate Amount USD
        settlement_df['Estimate_Amount(usd)'] = settlement_df['PayoutRoundAmt'] / settlement_df['APIRATE']
        
        #Identify duplicates
        settlement_df['is_duplicate_pin'] = settlement_df['Pin Number'].duplicated(keep=False)
        
        # Step 4c.i: Tag Post-Cancel type in duplicates as Should Reconcile
        settlement_df['Reconcile_Tag'] = None
        reconcile_postcancel_filt = (settlement_df['is_duplicate_pin']) & (settlement_df['Status'] == 'post-cancel')
        settlement_df.loc[reconcile_postcancel_filt, 'Reconcile_Tag'] = "Should Reconcile"

        # Step 4d: Tag non-duplicates as Should Reconcile
        settlement_df.loc[~settlement_df['is_duplicate_pin'], 'Reconcile_Tag'] = 'Should Reconcile'
        
        self.settlement_df = settlement_df
        

    def match_transactions(self):
        """Step 5: Match transactions between files"""
        #Filter only Should Reconcile
        statement_reconcile = self.clean_statement_df[
            self.clean_statement_df['Reconcile_Tag'] == 'Should Reconcile'
        ].copy()
        
        settlement_reconcile = self.settlement_df[
            self.settlement_df['Reconcile_Tag'] == 'Should Reconcile'
        ].copy()
        
        statement_pins = set(statement_reconcile['Partner_Pin'].dropna())
        settlement_pins = set(settlement_reconcile['Pin Number'].dropna())
        
        self.clean_statement_df['Match_Status'] = None
        self.settlement_df['Match_Status'] = None
        
        #Present in Both
        both_pins = statement_pins & settlement_pins
        self.clean_statement_df.loc[
            self.clean_statement_df['Partner_Pin'].isin(both_pins) & 
            (self.clean_statement_df['Reconcile_Tag'] == 'Should Reconcile'), 'Match_Status'] = 'Present in Both'
        
        self.settlement_df.loc[
            self.settlement_df['Pin Number'].isin(both_pins) & 
            (self.settlement_df['Reconcile_Tag'] == 'Should Reconcile'), 'Match_Status'] = 'Present in Both'
        
        #In Settlement but not in Statement
        settlement_only_pins = settlement_pins - statement_pins
        self.settlement_df.loc[
            self.settlement_df['Pin Number'].isin(settlement_only_pins) & 
            (self.settlement_df['Reconcile_Tag'] == 'Should Reconcile'), 'Match_Status'] = "Present in the Settlement File but not in the Partner Statement File"
        
        # In Statement but NOT in Settlement
        statement_only_pins = statement_pins - settlement_pins
        self.clean_statement_df.loc[
            self.clean_statement_df['Partner_Pin'].isin(statement_only_pins) & 
            (self.clean_statement_df['Reconcile_Tag'] == 'Should Reconcile'), 'Match_Status'] = "Not Present in the Settlement File but Present in the Partner Statement File"
        

    def get_results(self):
        """Steps 5,6 and 7: Get categorized results"""
        #Step 5 Results
        present_in_both_statement = self.clean_statement_df[self.clean_statement_df['Match_Status'] == 'Present in Both'].copy()
        
        present_in_both_settlement = self.settlement_df[self.settlement_df['Match_Status'] == 'Present in Both'].copy()
        
        present_in_settlement_only = self.settlement_df[
            self.settlement_df['Match_Status'] == 'Present in the Settlement File but not in the Partner Statement File'
        ].copy()
        
        present_in_statement_only = self.clean_statement_df[
            self.clean_statement_df['Match_Status'] == 'Not Present in the Settlement File but Present in the Partner Statement File'
        ].copy()
        
        #Step 6 Amount Comparison
        comparison = present_in_both_statement.merge(
            present_in_both_settlement[['Pin Number', 'Estimate_Amount(usd)']], 
            left_on='Partner_Pin', 
            right_on='Pin Number', 
            how='left',
            suffixes=('_statement', '_settlement')
        )
        
        comparison['Amount_Difference'] = comparison['Settle.Amt'] - comparison['Estimate_Amount(usd)']
        
        amount_comparison = comparison[['Partner_Pin', 'Settle.Amt', 'Estimate_Amount(usd)', 'Amount_Difference']].copy()
        
        #Step 7: Variance - In Settlement but NOT in Statement
        variance = present_in_settlement_only.copy()
        
        return {
            'present_in_both_statement': present_in_both_statement,
            'present_in_both_settlement': present_in_both_settlement,
            'present_in_settlement_only': present_in_settlement_only,
            'present_in_statement_only': present_in_statement_only,
            'amount_comparison': amount_comparison,
            'variance': variance
        }
    
    def run(self):
        """Execute full reconciliation process"""
        self.process_statement_file()
        self.process_settlement_file()
        self.match_transactions()
        return self.get_results()