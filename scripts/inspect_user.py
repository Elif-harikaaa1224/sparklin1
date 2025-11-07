import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import AsyncMongoDB

async def main():
    mongo = AsyncMongoDB()
    users = mongo.get_collection("users")
    user = await users.find_one({"referral_code": "RbmNCXJI"})
    print(user)

if __name__ == "__main__":
    asyncio.run(main())
