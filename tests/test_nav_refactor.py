
import pytest
from datetime import datetime
from app.services.mappers import NavReportMapper
from app.models import NavReportType
from app.services.portfolio_analysis import get_nav_history_stats

class TestNavRefactor:
    
    def test_mapper_csv_format(self):
        """Test mapping a dictionary resembling CSV row."""
        raw = {
            "ClientAccountID": "U123456",
            "AccountAlias": "MyAccount",
            "CurrencyPrimary": "USD",
            "FromDate": "20250101",
            "ToDate": "20250131",
            "StartingValue": "10000.00",
            "EndingValue": "11000.00",
            "Mtm": "1000.00",
            "TWR": "10.0"
        }
        
        doc = NavReportMapper.map_to_mongo(
            raw_data=raw,
            source_type="TEST",
            ibkr_report_type=NavReportType.NAV_30D,
            query_id="999",
            query_name="Monthly"
        )
        
        assert doc["account_id"] == "U123456"
        assert doc["ibkr_report_type"] == "Nav30D"
        assert doc["_report_date"] == "2025-01-31"
        assert doc["starting_value"] == 10000.0
        assert doc["ending_value"] == 11000.0
        assert doc["mtm"] == 1000.0
        assert doc["twr"] == 10.0
        
    def test_mapper_xml_format_with_pascal_mapping(self):
        """Test mapping a dictionary resembling XML attributes (after pascal normalization)."""
        # Simulated 'pascal' dict creation in ibkr_service
        raw = {
            "ClientAccountID": "U987654",
            "EndingValue": "5050.50",
            "StartingValue": "5000.00",
            "Mtm": "50.50",
            "TWR": "1.01",
            "ToDate": "2025-02-15" # XML date sometimes hyphens
        }
        
        doc = NavReportMapper.map_to_mongo(
            raw_data=raw,
            source_type="TEST_XML",
            ibkr_report_type=NavReportType.NAV_1D,
            query_id="888"
        )
        
        assert doc["account_id"] == "U987654"
        assert doc["ending_value"] == 5050.5
        assert doc["_report_date"] == "2025-02-15"
        
    def test_portfolio_stats_logic(self):
        """Test get_nav_history_stats with mocked database."""
        from unittest.mock import patch, MagicMock
        
        with patch("app.services.portfolio_analysis.MongoClient") as mock_client:
            mock_db = mock_client.return_value.get_default_database.return_value
            
            # Mock collections
            # We need to mock find_one calls for each report type
            
            def mock_find_one(query, sort=None):
                rtype = query.get("ibkr_report_type")
                if rtype == "NAV1D":
                    return {
                        "ending_value": 100.0,
                        "starting_value": 99.0,
                        "twr": 1.01,
                        "ibkr_report_type": "NAV1D"
                    }
                if rtype == "Nav7D": # Enum value
                    return {
                        "ending_value": 100.0,
                        "starting_value": 95.0,
                        "twr": 5.26,
                        "ibkr_report_type": "Nav7D"
                    }
                return None
                
            mock_db.ibkr_nav_history.find_one.side_effect = mock_find_one
            
            # Mock Aggregate for History
            mock_db.ibkr_nav_history.aggregate.return_value = [
                {"date": "2025-01-01", "nav": 90.0},
                {"date": "2025-01-02", "nav": 100.0}
            ]
            
            stats = get_nav_history_stats()
            
            assert stats["current_nav"] == 100.0
            assert stats["change_1d"] == 1.01
            assert stats["change_7d"] == 5.26
            assert stats["change_30d"] is None # Not mocked
            assert len(stats["history"]) == 2
