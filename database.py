import os
import asyncio
import threading
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure

load_dotenv()

class AsyncMongoDB:
    """
    Async Singleton MongoDB connection handler using Motor.
    Automatically reuses a single connection across your app.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, uri=None, db_name=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AsyncMongoDB, cls).__new__(cls)
                    cls._instance._init_connection(uri, db_name)
        return cls._instance

    def _init_connection(self, uri=None, db_name=None):
        print(f"[DEBUG] Initializing MongoDB connection with URI: {os.getenv('MONGO_URI')}")
        self.uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.db_name = db_name or os.getenv("MONGO_DB_NAME", "sparklin")
        self.client = AsyncIOMotorClient(self.uri)
        self.db = self.client[self.db_name]

    async def ping(self):
        """Verify connection is alive."""
        try:
            await self.db.command("ping")
            print(f"✅ Connected to MongoDB (async): {self.uri}")
        except ConnectionFailure as e:
            print(f"❌ MongoDB connection failed: {e}")
            raise

    def get_collection(self, name):
        """Get a Motor async collection."""
        return self.db[name]

    async def close(self):
        """Close the async MongoDB connection."""
        self.client.close()
        print("🔒 MongoDB connection closed (async).")
        AsyncMongoDB._instance = None
