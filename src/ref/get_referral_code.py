from database import AsyncMongoDB

MONGO = AsyncMongoDB()

# --- Get existing referral code ---
async def get_referral_code(user_id: str) -> dict | None:
    mongo = AsyncMongoDB()
    collection = mongo.get_collection("users")

    user = await collection.find_one({"user_id": str(user_id)})
    if user:
        return {
            "code": user.get("referral_code"),
            "count": user.get("referrals_count", 0),
            "referrals": user.get("referrals", []),
        }
    else:
        return None