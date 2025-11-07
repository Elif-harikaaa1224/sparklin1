import os
from datetime import datetime
from uuid import uuid4

from database import AsyncMongoDB
from src.ref.create_ref_code import generate_random_code

MONGO = AsyncMongoDB()


def _generate_storage_key() -> str:
    return uuid4().hex


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
    user_id_str = str(user_id)

    try:
        # Check if user already exists
        existing_user = await users_collection.find_one({"user_id": user_id_str})

        if existing_user:
            updates = {}
            storage_key = existing_user.get("storage_key")
            if not storage_key:
                storage_key = _generate_storage_key()
                updates["storage_key"] = storage_key

            if "referrals_count" not in existing_user:
                updates["referrals_count"] = 0
            if "referrals" not in existing_user:
                updates["referrals"] = []

            if updates:
                await users_collection.update_one(
                    {"_id": existing_user["_id"]},
                    {"$set": updates},
                )
                existing_user.update(updates)

            return {
                "success": False,
                "message": f"User {user_id} already exists",
                "user": existing_user,
                "storage_key": existing_user.get("storage_key"),
                "referrals_count": existing_user.get("referrals_count", 0),
            }

        # ---- Create new user ----
        referrer_user = None
        referrer_user_id = None
        if referral_code:
            referrer_user = await users_collection.find_one({"referral_code": referral_code})
            if not referrer_user:
                referral_code = None
                referrer_user = None
            else:
                referrer_user_id = referrer_user.get("user_id")

        storage_key = _generate_storage_key()

        user_doc = {
            "user_id": user_id_str,
            "username": username,
            "created_at": datetime.utcnow(),
            "referral_code": generate_random_code(),
            "referred_by": referral_code,
            "referred_by_user_id": referrer_user_id,
            "storage_key": storage_key,
            "referrals_count": 0,
            "referrals": [],
        }

        result = await users_collection.insert_one(user_doc)

        if referrer_user:
            # Ensure referrer document has the necessary fields before increment
            if "referrals_count" not in referrer_user:
                await users_collection.update_one(
                    {"_id": referrer_user["_id"]},
                    {"$set": {"referrals_count": 0}},
                )
                referrer_user["referrals_count"] = 0
            if "referrals" not in referrer_user:
                await users_collection.update_one(
                    {"_id": referrer_user["_id"]},
                    {"$set": {"referrals": []}},
                )
                referrer_user["referrals"] = []

            await users_collection.update_one(
                {"_id": referrer_user["_id"]},
                {
                    "$inc": {"referrals_count": 1},
                    "$addToSet": {"referrals": user_id_str},
                },
            )

        return {
            "success": True,
            "message": f"User {user_id} created successfully",
            "user_id": user_id_str,
            "inserted_id": str(result.inserted_id),
            "storage_key": storage_key,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating user: {str(e)}"
        }