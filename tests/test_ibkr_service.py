import pytest
from unittest.mock import MagicMock, patch
from app.services.ibkr_service import fetch_flex_report, parse_and_store_holdings, parse_and_store_trades

# Sample XML Data
SAMPLE_HOLDINGS_XML = """
<FlexQueryResponse queryName="Daily_Portfolio" type="AF">
  <FlexStatements>
    <FlexStatement date="2026-01-28">
      <OpenPositions>
        <OpenPosition accountId="U123456" symbol="AAPL" position="100" costBasisPrice="150.00" markPrice="160.00" markValue="16000" percentOfNAV="10.5" fifoPnlUnrealized="1000.00"/>
        <OpenPosition accountId="U123456" symbol="USD" position="5000" costBasisPrice="1.0" markPrice="1.0" markValue="5000" percentOfNAV="3.2" fifoPnlUnrealized="0.00"/>
      </OpenPositions>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>
"""

SAMPLE_TRADES_XML = """
<FlexQueryResponse queryName="Recent_Trades" type="AF">
  <FlexStatements>
    <FlexStatement date="2026-01-28">
      <Trades>
        <Trade tradeID="T999" symbol="TSLA" dateTime="2026-01-28;10:00:00" quantity="10" tradePrice="200.00" ibCommission="1.00" buySell="BUY" orderType="LMT" exchange="NASDAQ"/>
      </Trades>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>
"""

@patch("app.services.ibkr_service.requests.get")
def test_fetch_flex_report_success(mock_get):
    """Test the two-step fetch process."""
    # Mock Step 1: Reference Code
    mock_response_1 = MagicMock()
    mock_response_1.status_code = 200
    mock_response_1.content = b'<FlexStatementResponse><Status>Success</Status><ReferenceCode>REF123</ReferenceCode></FlexStatementResponse>'
    
    # Mock Step 2: Actual Report
    mock_response_2 = MagicMock()
    mock_response_2.status_code = 200
    mock_response_2.content = b'<XML>Report</XML>'
    
    mock_get.side_effect = [mock_response_1, mock_response_2]
    
    result = fetch_flex_report("query_id", "token")
    assert result == b'<XML>Report</XML>'

@patch("app.services.ibkr_service.MongoClient")
def test_parse_and_store_holdings(mock_mongo):
    """Test parsing logic and DB insertion."""
    mock_db = mock_mongo.return_value.get_default_database.return_value
    mock_collection = mock_db.ibkr_holdings
    
    parse_and_store_holdings(SAMPLE_HOLDINGS_XML.encode('utf-8'))
    
    # Verify Insertion
    assert mock_collection.insert_many.called
    args = mock_collection.insert_many.call_args[0][0]
    assert len(args) == 2
    assert args[0]["symbol"] == "AAPL"
    assert args[0]["quantity"] == 100.0
    assert args[0]["report_date"] == "2026-01-28"

@patch("app.services.ibkr_service.MongoClient")
def test_parse_and_store_trades(mock_mongo):
    """Test trades parsing and idempotency."""
    mock_db = mock_mongo.return_value.get_default_database.return_value
    mock_collection = mock_db.ibkr_trades
    
    parse_and_store_trades(SAMPLE_TRADES_XML.encode('utf-8'))
    
    # Verify Upsert
    assert mock_collection.update_one.called
    call_args = mock_collection.update_one.call_args
    query = call_args[0][0]
    update = call_args[0][1]
    
    assert query["trade_id"] == "T999"
    assert update["$set"]["symbol"] == "TSLA"
    assert update["$set"]["price"] == 200.0
