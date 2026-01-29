import sys
import os

# Ensure we can import from app
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from pymongo import MongoClient
from app.auth.utils import get_password_hash
from app.config import settings

def seed_users():
    print("Connecting to MongoDB...")
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    users_collection = db["users"]

    # Define Test Users
    users_to_seed = [
        {
            "username": "admin",
            "password": "admin123", # Matches current default
            "role": "admin",
            "disabled": False
        },
        {
            "username": "user_portfolio",
            "password": "password123",
            "role": "portfolio",
            "disabled": False
        },
        {
            "username": "user_analyst",
            "password": "password123",
            "role": "analyst",
            "disabled": False
        },
        {
            "username": "user_basic",
            "password": "password123",
            "role": "basic",
            "disabled": False
        }
    ]

    print(f"Seeding {len(users_to_seed)} users...")
    
    for u in users_to_seed:
        hashed = get_password_hash(u["password"])
        
        user_doc = {
            "username": u["username"],
            "hashed_password": hashed,
            "role": u["role"],
            "disabled": u["disabled"]
        }
        
        # Upsert based on username
        result = users_collection.update_one(
            {"username": u["username"]},
            {"$set": user_doc},
            upsert=True
        )
        
        action = "Updated" if result.matched_count > 0 else "Created"
        print(f"[{u['role'].upper()}] User '{u['username']}': {action}")

    print("User seeding complete.")

if __name__ == "__main__":
    seed_users()
