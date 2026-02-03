from pymongo import MongoClient
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def get_db():
    """
    Dependency to get a MongoDB database reference.
    Yields the database object.
    """
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    try:
        yield db
    finally:
        client.close()
