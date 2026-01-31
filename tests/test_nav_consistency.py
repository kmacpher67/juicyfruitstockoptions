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
        # 1. Verify ibkr_nav_history Upsert (Historical Start - Open)
        # Expect 2026-01-28 (FromDate) with nav_open=100000
        start_call = [args for args in mock_db.ibkr_nav_history.update_one.call_args_list if args[0][0]['report_date'] == '2026-01-28']
        self.assertTrue(start_call, "CSV: Failed to save Historical Start Record (2026-01-28)")
        self.assertEqual(start_call[0][0][1]['$set']['nav_open'], 100000.0)
        
        # 2. Verify ibkr_nav_history Upsert (Current End - Close)
        # Expect 2026-01-29 with nav_close=100500
        end_call = [args for args in mock_db.ibkr_nav_history.update_one.call_args_list if args[0][0]['report_date'] == '2026-01-29']
        self.assertTrue(end_call, "CSV: Failed to save Current End Record")
        self.assertEqual(end_call[0][0][1]['$set']['nav_close'], 100500.0)
        
        # 3. Verify ibkr_raw_flex_reports Upsert
        # Expect key ClientAccountID=U123456
        raw_call = mock_db.ibkr_raw_flex_reports.update_one.call_args
        self.assertIsNotNone(raw_call, "CSV: Failed to save RAW report")
        self.assertEqual(raw_call[0][1]['$set']['StartingValue'], "100000")
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
        # 1. Verify ibkr_nav_history Upsert (Historical Start)
        # XML Logic: FromDate=20251230 -> 2025-12-30
        
        # Check the Update Payload ($set), matches 'source'
        start_call = [args for args in mock_db.ibkr_nav_history.update_one.call_args_list if args[0][1]['$set'].get('source') == 'FLEX_XML_PERIOD_START']
        self.assertTrue(start_call, "XML: Failed to save Historical Start Record")
        
        # Verify Date used was FromDate (2025-12-30)
        self.assertEqual(start_call[0][0][0]['report_date'], '2025-12-30')
        self.assertEqual(start_call[0][0][1]['$set']['nav_open'], 90000.0)
        
        # 2. Verify ibkr_raw_flex_reports Upsert
        # Expect raw xml data save
        raw_call = mock_db.ibkr_raw_flex_reports.update_one.call_args
        self.assertIsNotNone(raw_call, "XML: Failed to save RAW report")
        self.assertEqual(raw_call[0][1]['$set']['startingValue'], "90000")
        print("XML Consistency: PASSED")

if __name__ == '__main__':
    unittest.main()
