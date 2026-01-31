import pytest
from unittest.mock import MagicMock, patch
from app.services.ibkr_service import parse_and_store_nav
from app.models import NavReportType

# Sample XML with TWR
SAMPLE_NAV_XML = """
<FlexQueryResponse queryName="NAV_Report" type="AF">
  <FlexStatements>
    <FlexStatement date="2026-01-30">
      <ChangeInNAV accountId="U123456" 
                   startingValue="100000.00" 
                   endingValue="101000.00" 
                   mtm="1000.00" 
                   TWR="1.0" 
                   fromDate="2026-01-30" 
                   toDate="2026-01-30"/>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>
"""

@patch("app.services.ibkr_service.MongoClient")
def test_parse_nav_xml_extracts_twr(mock_mongo):
    """Verify TWR is correctly parsed from XML and stored."""
    # Setup Mock DB
    mock_db = mock_mongo.return_value.get_default_database.return_value
    mock_collection = mock_db.ibkr_nav_history
    
    # Execute
    meta = {"ibkr_report_type": NavReportType.NAV_1D, "ibkr_query_id": "123"}
    parse_and_store_nav(SAMPLE_NAV_XML.encode('utf-8'), metadata=meta)
    
    # It might be called twice (Current Day + Previous Day Backfill)
    # We want to verify the Current Day (2026-01-30) record
    
    found = False
    for call in mock_collection.update_one.call_args_list:
        args, _ = call
        # args[0] is filter, args[1] is update {"$set": ...}
        update_doc = args[1]["$set"]
        
        if update_doc.get("_report_date") == "2026-01-30":
            found = True
            assert update_doc["account_id"] == "U123456"
            assert update_doc.get("twr") == 1.0
            assert update_doc["ending_value"] == 101000.00
            assert update_doc["ibkr_report_type"] == "NAV1D"
            break
            
    assert found, "Did not find update call for 2026-01-30"

