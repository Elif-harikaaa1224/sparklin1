from database import AsyncMongoDB

MONGO = AsyncMongoDB()

# --- Get existing referral code ---
async def get_referral_code(user_id: str) -> str:
    mongo = AsyncMongoDB()
    collection = mongo.get_collection("users")

    user = await collection.find_one({"user_id": str(user_id)})
    if user:
        return user["referral_code"]
    else:
        return None