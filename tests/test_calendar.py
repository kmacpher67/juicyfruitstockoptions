from datetime import datetime
from pathlib import Path
from unittest.mock import patch


@patch("pymongo.MongoClient")
def test_get_dividend_calendar_generation(mock_mongo, monkeypatch, tmp_path):
    """Generate the calendar when today's cached file is missing."""

    monkeypatch.chdir(tmp_path)
    expected_file_path = Path("xdivs/corporate_events_2099-01-01.ics")

    with patch("app.services.dividend_scanner.DividendScanner") as MockScanner:
        mock_instance = MockScanner.return_value

        def create_dummy_file():
            expected_file_path.parent.mkdir(exist_ok=True)
            expected_file_path.write_text("DUMMY ICS CONTENT")
            return str(expected_file_path)

        mock_instance.generate_corporate_events_calendar.side_effect = create_dummy_file

        with patch("app.api.routes.datetime") as mock_dt_module:
            mock_dt_module.utcnow.return_value = datetime(2099, 1, 1)

            from app.api.routes import get_dividend_calendar

            response = get_dividend_calendar()

        assert response.path == str(expected_file_path)
        MockScanner.assert_called_once()
        mock_instance.generate_corporate_events_calendar.assert_called_once()
        mock_mongo.assert_not_called()


@patch("pymongo.MongoClient")
def test_get_dividend_calendar_cache_hit(mock_mongo, monkeypatch, tmp_path):
    """Serve the cached file without generating a fresh calendar."""

    monkeypatch.chdir(tmp_path)
    expected_file = Path("xdivs/corporate_events_2099-01-02.ics")
    expected_file.parent.mkdir(exist_ok=True)
    expected_file.write_text("DUMMY CONTENT")

    with patch("app.services.dividend_scanner.DividendScanner") as MockScanner:
        with patch("app.api.routes.datetime") as mock_dt_module:
            mock_dt_module.utcnow.return_value = datetime(2099, 1, 2)

            from app.api.routes import get_dividend_calendar

            response = get_dividend_calendar()

        mock_mongo.assert_not_called()
        MockScanner.assert_not_called()
        assert response.path == str(expected_file)
