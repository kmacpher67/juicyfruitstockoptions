from app.models.opportunity import JuicyOpportunity, OpportunityStatus
from pymongo import MongoClient
from app.config import settings
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class OpportunityService:
    def __init__(self, db_client=None):
        # Allow injection or create new client
        self.client = db_client or MongoClient(settings.MONGO_URI)
        self.db = self.client.get_default_database("stock_analysis")
        self.collection = self.db.opportunities
        
        # Ensure Indexes
        self.collection.create_index("symbol")
        self.collection.create_index("timestamp")
        self.collection.create_index("status")
        self.collection.create_index("trigger_source")

    def create_opportunity(self, opportunity: JuicyOpportunity) -> str:
        """Persist a new opportunity to the database."""
        try:
            data = opportunity.dict()
            # Ensure timestamp is present
            if not data.get("timestamp"):
                data["timestamp"] = datetime.utcnow()
                
            result = self.collection.insert_one(data)
            logger.info(f"Created opportunity {result.inserted_id} for {opportunity.symbol} via {opportunity.trigger_source}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to create opportunity: {e}", exc_info=True)
            raise

    def get_opportunities(self, source: Optional[str] = None, status: Optional[str] = None, limit: int = 100) -> List[dict]:
        """Retrieve opportunities with optional filtering."""
        query = {}
        if source:
            query["trigger_source"] = source
        if status:
            query["status"] = status
            
        cursor = self.collection.find(query).sort("timestamp", -1).limit(limit)
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
