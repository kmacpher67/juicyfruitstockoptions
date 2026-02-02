from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import settings
from app.models import TokenData, User
from app.auth.utils import verify_password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


import logging
logger = logging.getLogger(__name__)

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    logger.debug("Validating token...")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token validation failed: User not found in token")
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # Fetch user from MongoDB
    from pymongo import MongoClient
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        user_doc = db.users.find_one({"username": token_data.username})
        
        if user_doc is None:
            logger.warning("Token validation failed: User not found in DB")
            raise credentials_exception
            
        return User(
            username=user_doc["username"],
            role=user_doc.get("role", "basic"),
            disabled=user_doc.get("disabled", False)
        )
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}", exc_info=True)
        raise credentials_exception

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
