import os
from datetime import datetime

from database import AsyncMongoDB
from src.ref.create_ref_code import generate_random_code

MONGO = AsyncMongoDB()

async def create_user(user_id: int, username: str = None, referral_code: str = None):
    """
    Create a new user in MongoDB users collection if user_id doesn't exist.
    
    Args:
        user_id (int): Telegram user ID
        username (str, optional): Telegram username
        **kwargs: Additional user fields (e.g., first_name, last_name)
    
    Returns:
        dict: Result with 'success' boolean and 'message' string
    """
    users_collection = MONGO.get_collection("users")
    
    try:
        # Check if user already exists
        existing_user = await users_collection.find_one({"user_id": str(user_id)})
        
        if existing_user:
            return {
                "success": False,
                "message": f"User {user_id} already exists",
                "user": existing_user
            }
        
        # Create new user document
        user_doc = {
            "user_id": str(user_id),
            "username": username,
            "created_at": datetime.utcnow(),
            "referral_code": generate_random_code(),
            "referred_by": referral_code
        }
        
        # Insert the new user
        result = await users_collection.insert_one(user_doc)
        
        return {
            "success": True,
            "message": f"User {user_id} created successfully",
            "user_id": str(user_id),
            "inserted_id": str(result.inserted_id)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating user: {str(e)}"
        }