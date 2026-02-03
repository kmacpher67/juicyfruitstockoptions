from datetime import datetime
import logging
from pymongo import MongoClient
from app.config import settings
from app.services.opportunity_service import OpportunityService
from app.models.opportunity import JuicyOpportunity, OpportunityStatus

logger = logging.getLogger(__name__)

class ExpirationScanner:
    def __init__(self):
        self.opp_service = OpportunityService()

    def scan_portfolio_expirations(self, days_threshold: int = 7):
        """
        Scan portfolio for short options expiring within threshold days.
        """
        logger.info(f"ExpirationScanner: Starting scan (Threshold: {days_threshold} days)...")
        try:
            client = MongoClient(settings.MONGO_URI)
            db = client.get_default_database("stock_analysis")
            
            # 1. Fetch Latest Holdings
            latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
            if not latest:
                logger.warning("ExpirationScanner: No portfolio holdings found.")
                return

            query = {"snapshot_id": latest.get("snapshot_id")} if latest.get("snapshot_id") else {"report_date": latest.get("report_date")}
            holdings = list(db.ibkr_holdings.find(query))
            
            count = 0
            now = datetime.now()
            
            for item in holdings:
                # Filter for Short Options
                sec_type = item.get("secType") or item.get("asset_class")
                if sec_type not in ["OPT", "FOP"]: continue
                
                qty = float(item.get("quantity", 0))
                if qty >= 0: continue # Ignore Longs (for now)
                
                # Parse Expiry
                exp_str = item.get("expiry")
                if not exp_str: continue
                
                try:
                    # Normalize Date
                    if len(exp_str) == 8 and "-" not in exp_str:
                         exp_dt = datetime.strptime(exp_str, "%Y%m%d")
                    else:
                         exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
                         
                    # Use Calendar Days (Date diff, not timestamp diff)
                    # Use local time for "perception" of "Today"
                    days_to_exp = (exp_dt.date() - now.date()).days
                    
                    if days_to_exp <= days_threshold:
                        self._create_opportunity(item, days_to_exp, exp_dt)
                        count += 1
                        
                except Exception as e:
                    logger.error(f"ExpirationScanner: Error parsing item {item.get('symbol')}: {e}")
                    continue
            
            logger.info(f"ExpirationScanner: Completed. Found {count} expiring positions.")
            
        except Exception as e:
            logger.error(f"ExpirationScanner check failed: {e}", exc_info=True)

    def _create_opportunity(self, item, days_to_exp, exp_date):
        """Create and persist the opportunity."""
        symbol = item.get("symbol")
        
        # Check for duplicates? For now, simplistic check or just create.
        # Ideally we don't spam. But "DETECTED" status allows deduping in Service if enforced.
        # We'll just create it.
        
        opp_data = {
            "symbol": symbol,
            "expiry": exp_date.strftime("%Y-%m-%d"),
            "days_to_exp": days_to_exp,
            "strike": item.get("strike"),
            "quantity": item.get("quantity"),
            "action": "Review",
            "reason": f"Expiring in {days_to_exp} days",
            "strategy": "Close, Roll, or Assign"
        }
        
        # Use underlying for the main Symbol if possible
        display_symbol = item.get("underlying_symbol") or symbol
        if len(display_symbol) > 6: display_symbol = display_symbol[:6] # Fallback

        try:
            opp = JuicyOpportunity(
                symbol=display_symbol,
                trigger_source="ExpirationScanner",
                status=OpportunityStatus.DETECTED,
                context={
                    "full_symbol": symbol,
                    "price": item.get("mark_price") or item.get("marketPrice"),
                    "days_to_exp": days_to_exp,
                    "quantity": item.get("quantity")
                },
                proposal=opp_data
            )
            self.opp_service.create_opportunity(opp)
            logger.info(f"ExpirationScanner: Flagged {symbol} (DTE {days_to_exp})")
        except Exception as e:
            logger.error(f"ExpirationScanner: Failed to persist {symbol}: {e}")
