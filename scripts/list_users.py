import asyncio
import os
import sys
from pprint import pprint

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import AsyncMongoDB


async def main():
    mongo = AsyncMongoDB()
    users_col = mongo.get_collection("users")
    users = await users_col.find().to_list(length=None)
    for user in users:
        pprint({k: (str(v)) for k, v in user.items()})


if __name__ == "__main__":
    asyncio.run(main())

