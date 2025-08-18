import os
from pymongo import MongoClient


def get_mongo_client() -> MongoClient:
    """Return a MongoDB client using MONGO_URI environment variable."""
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    return MongoClient(uri)
