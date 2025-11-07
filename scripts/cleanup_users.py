import asyncio
import os
import sys
from pprint import pprint
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import AsyncMongoDB


TARGET_USERNAME = "vBesky"


async def main():
    mongo = AsyncMongoDB()
    users_col = mongo.get_collection("users")

    # Remove users with other usernames
    delete_result = await users_col.delete_many({"username": {"$ne": TARGET_USERNAME}})
    print(f"Deleted {delete_result.deleted_count} non-target user(s)")

    users = await users_col.find({"username": TARGET_USERNAME}).sort("created_at", 1).to_list(length=None)

    if not users:
        print("No users left for target username; nothing to keep.")
        return

    # Keep the most recent document
    keep_user = users[-1]
    to_remove = users[:-1]

    for doc in to_remove:
        await users_col.delete_one({"_id": doc["_id"]})
        print(f"Removed duplicate user document: {doc['_id']}")

    if "storage_key" not in keep_user or not keep_user["storage_key"]:
        storage_key = uuid4().hex
        await users_col.update_one({"_id": keep_user["_id"]}, {"$set": {"storage_key": storage_key}})
        keep_user["storage_key"] = storage_key
        print(f"Assigned new storage_key to keeper: {storage_key}")

    print("Remaining user record:")
    pprint({k: (str(v)) for k, v in keep_user.items()})


if __name__ == "__main__":
    asyncio.run(main())


