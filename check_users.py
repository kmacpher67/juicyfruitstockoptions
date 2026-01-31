from pymongo import MongoClient
import os
from app.config import settings

def list_users():
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        users = list(db.users.find({}, {"username": 1, "role": 1}))
        print("Existing Users:")
        for u in users:
            print(f"- {u['username']} (Role: {u.get('role', 'unknown')})")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_users()
