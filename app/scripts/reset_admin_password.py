
import sys
import logging
from pymongo import MongoClient
from app.config import settings
from app.auth.utils import get_password_hash

# Setup simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_password")

def reset_password(username, new_password):
    logger.info(f"Attempting to reset password for user: {username}")
    
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        users_col = db.users
        
        user = users_col.find_one({"username": username})
        if not user:
            logger.error(f"User '{username}' not found.")
            return False
            
        hashed = get_password_hash(new_password)
        
        result = users_col.update_one(
            {"username": username},
            {"$set": {"hashed_password": hashed}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Password for '{username}' updated successfully.")
            return True
        else:
            logger.warning("Password was not updated (maybe it was the same?)")
            return True
            
    except Exception as e:
        logger.error(f"Failed to reset password: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m app.scripts.reset_admin_password <username> <new_password>")
        sys.exit(1)
        
    username = sys.argv[1]
    password = sys.argv[2]
    
    if reset_password(username, password):
        sys.exit(0)
    else:
        sys.exit(1)
