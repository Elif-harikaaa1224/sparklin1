import asyncio
import os
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import AsyncMongoDB


async def rebuild_referrals():
    mongo = AsyncMongoDB()
    users_collection = mongo.get_collection("users")

    users = await users_collection.find({}).to_list(length=None)

    code_to_user = {}
    for user in users:
        code = user.get("referral_code")
        if code:
            code_to_user[code] = user

    referrals_mapping = defaultdict(list)

    for user in users:
        referred_by = user.get("referred_by")
        if referred_by:
            referrer = code_to_user.get(referred_by)
            if referrer:
                referrer_id = referrer.get("user_id")
                referrals_mapping[referrer_id].append(user.get("user_id"))

    for user in users:
        user_id = user.get("user_id")
        referrals = referrals_mapping.get(user_id, [])
        await users_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "referrals_count": len(referrals),
                    "referrals": referrals,
                }
            },
        )


if __name__ == "__main__":
    asyncio.run(rebuild_referrals())
