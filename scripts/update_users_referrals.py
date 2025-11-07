import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import AsyncMongoDB

async def main():
    mongo = AsyncMongoDB()
    users = mongo.get_collection("users")

    await users.update_many(
        {"referrals_count": {"$exists": False}},
        {"$set": {"referrals_count": 0}},
    )
    await users.update_many(
        {"referrals": {"$exists": False}},
        {"$set": {"referrals": []}},
    )
    await users.update_many(
        {"referred_by": "None"},
        {"$set": {"referred_by": None}},
    )

if __name__ == "__main__":
    asyncio.run(main())
