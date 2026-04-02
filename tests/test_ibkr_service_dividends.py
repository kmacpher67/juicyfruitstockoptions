from unittest.mock import MagicMock, patch

from app.services.ibkr_service import parse_csv_dividends


DIVIDENDS_CSV = """Symbol,Description,Code,ExDate,PayDate,Quantity,GrossAmount,NetAmount,CurrencyPrimary,ClientAccountID,ActionID
AAPL,AAPL CASH DIVIDEND,PO,20260315,20260320,100,25.00,25.00,USD,U12345,A1
AAPL,AAPL CASH DIVIDEND,RE,20260315,20260320,100,25.00,25.00,USD,U12345,A1
MSFT,MSFT CASH DIVIDEND,RE,20260310,20260317,50,15.00,12.75,USD,U99999,
"""


@patch("app.services.ibkr_service.MongoClient")
def test_parse_csv_dividends_upserts_po_and_re_rows_with_normalized_dates(mock_mongo):
    mock_db = MagicMock()
    mock_mongo.return_value.get_default_database.return_value = mock_db

    parse_csv_dividends(DIVIDENDS_CSV)

    assert mock_db.ibkr_dividends.update_one.call_count == 3

    first_query, first_update = mock_db.ibkr_dividends.update_one.call_args_list[0][0][:2]
    second_query, second_update = mock_db.ibkr_dividends.update_one.call_args_list[1][0][:2]

    assert first_query == {"action_id": "A1", "code": "PO"}
    assert second_query == {"action_id": "A1", "code": "RE"}

    first_doc = first_update["$set"]
    second_doc = second_update["$set"]
    assert first_doc["ex_date"] == "2026-03-15"
    assert first_doc["pay_date"] == "2026-03-20"
    assert first_doc["account_id"] == "U12345"
    assert first_doc["currency"] == "USD"
    assert second_doc["code"] == "RE"


@patch("app.services.ibkr_service.MongoClient")
def test_parse_csv_dividends_falls_back_to_compound_query_when_action_id_missing(mock_mongo):
    mock_db = MagicMock()
    mock_mongo.return_value.get_default_database.return_value = mock_db

    parse_csv_dividends(DIVIDENDS_CSV)

    last_query, last_update = mock_db.ibkr_dividends.update_one.call_args_list[-1][0][:2]
    assert last_query == {
        "symbol": "MSFT",
        "pay_date": "2026-03-17",
        "gross_amount": 15.0,
        "code": "RE",
    }
    last_doc = last_update["$set"]
    assert last_doc["net_amount"] == 12.75
    assert last_doc["quantity"] == 50.0
