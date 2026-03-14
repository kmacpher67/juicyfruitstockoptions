import pytest
from app.services.ibkr_service import parse_csv_trades, parse_xml_trades
from unittest.mock import patch, MagicMock

CSV_TRADES = \"\"\"Symbol,Buy/Sell,TradeID,AccountID,Quantity,TradePrice,IBCommission,FifoPnlRealized,RealizedPnL,OrderType,AssetClass,Put/Call,NetCash,ClosePrice,Exchange
AAPL,BUY,1,U12345,10,150.0,-1.0,0,0,LMT,STK,,1500.0,155.0,NASDAQ
\"\"\"

XML_TRADES = \"\"\"<?xml version="1.0" encoding="UTF-8"?>
<FlexStatementResponse>
    <FlexStatements>
        <FlexStatement>
            <Trades>
                <Trade tradeID="2" accountId="U12345" symbol="AAPL" quantity="-10" tradePrice="160.0" ibCommission="-1.0" buySell="SELL" orderType="LMT" assetCategory="STK" putCall="" netCash="-1600.0" closePrice="158.0" exchange="ISLAND"/>
            </Trades>
        </FlexStatement>
    </FlexStatements>
</FlexStatementResponse>\"\"\"

@patch('app.services.ibkr_service.MongoClient')
def test_parse_csv_trades(mock_mongo):
    mock_db = MagicMock()
    mock_mongo.return_value.get_default_database.return_value = mock_db
    mock_collection = MagicMock()
    mock_db.ibkr_trades = mock_collection
    
    parse_csv_trades(CSV_TRADES)
    
    # Assert
    assert mock_collection.update_one.called
    args, kwargs = mock_collection.update_one.call_args
    query, update_stmt = args
    
    assert query == {"trade_id": "1"}
    doc = update_stmt["$set"]
    assert doc["asset_class"] == "STK"
    assert doc["put_call"] == ""
    assert doc["net_cash"] == 1500.0
    assert doc["close_price"] == 155.0
    assert doc["exchange"] == "NASDAQ"

@patch('app.services.ibkr_service.MongoClient')
def test_parse_xml_trades(mock_mongo):
    mock_db = MagicMock()
    mock_mongo.return_value.get_default_database.return_value = mock_db
    mock_collection = MagicMock()
    mock_db.ibkr_trades = mock_collection
    
    parse_xml_trades(XML_TRADES.encode('utf-8'))
    
    # Assert
    assert mock_collection.update_one.called
    args, kwargs = mock_collection.update_one.call_args
    query, update_stmt = args
    
    assert query == {"trade_id": "2"}
    doc = update_stmt["$set"]
    assert doc["asset_class"] == "STK"
    assert doc["put_call"] == ""
    assert doc["net_cash"] == -1600.0
    assert doc["close_price"] == 158.0
    assert doc["exchange"] == "ISLAND"
