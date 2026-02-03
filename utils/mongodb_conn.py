import dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
from functools import lru_cache
dotenv.load_dotenv()


class MongodbConnection:
    mongo_client = None
    is_connected = False
    def __init__(self):
        self.connect_to_database()
    
    def close_mongo_client(self):
        self.mongo_client.close()
    
    def get_database(self, database_name):
        return self.mongo_client[database_name]
    
    def get_collection(self, collection_name):
        return self.mongo_client[collection_name]
    
    def connect_to_database(self):
        try:
            self.mongodb_uri = os.getenv("MONGODB_URI")
            mongodb_uri = os.getenv("MONGODB_URI")
            if mongodb_uri:
                self.mongo_client = AsyncIOMotorClient(mongodb_uri)
            else:
                # Build URI từ các biến riêng lẻ
                host = os.getenv("MONGODB_HOST", "localhost")
                port = int(os.getenv("MONGODB_PORT", 27017))
                database = os.getenv("MONGODB_DATABASE", "rag_db")
                username = os.getenv("MONGODB_USERNAME", "")
                password = os.getenv("MONGODB_PASSWORD", "")
                auth_source = os.getenv("MONGODB_AUTH_SOURCE", "admin")
                    
                if username and password:
                    mongodb_uri = f"mongodb://{username}:{password}@{host}:{port}/{database}?authSource={auth_source}"
                else:
                    mongodb_uri = f"mongodb://{host}:{port}/{database}"
                self.mongo_client = AsyncIOMotorClient(mongodb_uri)
            self.is_connected = True
            return True
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            self.is_connected = False
            return None
        
    def get_mongo_client(self):
        return self.mongo_client


@lru_cache(maxsize=1)
def get_mongodb_connection() -> MongodbConnection:
    return MongodbConnection()