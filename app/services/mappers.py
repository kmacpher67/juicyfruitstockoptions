from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.models import NavReportType

class NavReportMapper:
    """
    Maps raw IBKR Flex Report data (CSV/XML) to the standardized Mongo schema.
    """

    @staticmethod
    def map_to_mongo(
        raw_data: Dict[str, Any],
        source_type: str,
        ibkr_report_type: NavReportType,
        query_id: str = None,
        query_name: str = None
    ) -> Dict[str, Any]:
        """
        Transform raw dictionary into uniformed Mongo document.
        """
        
        # Helper for extracting float safely
        def get_float(key: str, default=0.0) -> float:
            val = raw_data.get(key)
            if val is None or val == "":
                return default
            try:
                return float(val)
            except ValueError:
                return default
                
        # Helper for Date Format (ISO YYYY-MM-DD)
        def fmt_date(d_str: str) -> Optional[str]:
            if not d_str: return None
            # CSV usually YYYYMMDD, XML might be same or YYYY-MM-DD
            d_str = str(d_str).strip()
            if len(d_str) == 8 and d_str.isdigit():
                return f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
            return d_str

        # Mapping Fields
        # Keys might vary between CSV and XML slightly, so we check alternatives or sanitize in caller.
        # Assuming caller (ibkr_service) normalizes keys or we handle common ones here.
        # IBKR CSV keys are usually direct.
        
        acct_id = raw_data.get("ClientAccountID") or raw_data.get("AccountId")
        
        # Parse Dates
        from_date = fmt_date(raw_data.get("FromDate"))
        to_date = fmt_date(raw_data.get("ToDate") or raw_data.get("ReportDate") or raw_data.get("Date"))
        
        doc = {
            # Identity
            "account_id": acct_id,
            "ibkr_report_type": ibkr_report_type.value, # Store as string
            "_report_date": to_date, # Primary Index Date
            
            # Metadata
            "account_alias": raw_data.get("AccountAlias"),
            "currency": raw_data.get("CurrencyPrimary") or raw_data.get("currency"),
            "ibkr_query_id": query_id,
            "ibkr_query_name": query_name,
            
            # Dates
            "from_date": from_date,
            "to_date": to_date,
            
            # Values
            "starting_value": get_float("StartingValue"),
            "ending_value": get_float("EndingValue") or get_float("NAV"),
            "mtm": get_float("Mtm"),
            
            # Flows
            "deposits_withdrawals": get_float("DepositsWithdrawals"),
            "dividends": get_float("Dividends"),
            "interest": get_float("Interest"),
            "change_interest_accruals": get_float("ChangeInInterestAccruals"),
            "fees": get_float("OtherFees"),
            "commissions": get_float("Commissions"),
            
            # Performance
            "twr": get_float("TWR"),
            
            # System
            "_ingested_at": datetime.now(timezone.utc),
            "_source_type": source_type
        }
        
        return doc
