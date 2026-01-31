import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from app.services.ibkr_service import parse_csv_nav, parse_xml_nav
from app.config import settings

# Sample Data
SAMPLE_CSV_1D = """
"ClientAccountID","AccountAlias","Model","CurrencyPrimary","FromDate","ToDate","StartingValue","Mtm","EndingValue"
"U123456","TestAlias","","USD","20260128","20260129","100000","500","100500"
"""

SAMPLE_XML_30D = """
<FlexStatementResponse>
    <FlexStatement>
        <ChangeInNAV accountId="U123456" fromDate="20251230" toDate="20260129" startingValue="90000" endingValue="100500" currency="USD" />
    </FlexStatement>
</FlexStatementResponse>
"""

class TestNAVConsistency(unittest.TestCase):
    
    @patch('app.services.ibkr_service.MongoClient')
    def test_csv_consistency(self, mock_client):
        # Setup Mock DB
        mock_db = MagicMock()
        mock_client.return_value.get_default_database.return_value = mock_db
        mock_client.return_value.__getitem__.return_value = mock_db 
        
        # Run Parser
        parse_csv_nav(SAMPLE_CSV_1D.strip())
        
        # Assertions
        # 1. Verify ibkr_nav_history Upsert (Consolidated Record)
        # Old tests checked for separate Open and Close records. 
        # New Mapper consolidates into one record per day.
        # Expect 2026-01-29 with ending_value=100500
        end_call = [args for args in mock_db.ibkr_nav_history.update_one.call_args_list if args[0][0].get('_report_date') == '2026-01-29']
        self.assertTrue(end_call, "CSV: Failed to save Current End Record")
        self.assertEqual(end_call[0][0][1]['$set']['ending_value'], 100500.0)
        print("CSV Consistency: PASSED")

    @patch('app.services.ibkr_service.MongoClient')
    def test_xml_consistency(self, mock_client):
        # Setup Mock DB
        mock_db = MagicMock()
        mock_client.return_value.get_default_database.return_value = mock_db
        mock_client.return_value.__getitem__.return_value = mock_db
        
        # Run Parser
        parse_xml_nav(SAMPLE_XML_30D.strip())
        
        # Assertions
        # 1. Verify ibkr_nav_history Upsert (Consolidated)
        # XML Logic now uses Mapper to create one record
        
        # Check the Update Payload ($set), matches '_source_type' with underscore
        
        nav_call = [args for args in mock_db.ibkr_nav_history.update_one.call_args_list 
                      if args[0][1]['$set'].get('_source_type') == 'FLEX_XML' and args[0][1]['$set'].get('_report_date') == '2026-01-29']
        
        self.assertTrue(nav_call, "XML: Failed to save Consolidated NAV Record")
        
        # Verify Values
        self.assertEqual(nav_call[0][0][1]['$set']['starting_value'], 90000.0)
        self.assertEqual(nav_call[0][0][1]['$set']['ending_value'], 100500.0)
        print("XML Consistency: PASSED")

if __name__ == '__main__':
    unittest.main()
