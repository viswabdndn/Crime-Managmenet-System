import os
from datetime import timedelta
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""
    SECRET_KEY = os.getenv("SECRET_KEY", "default-fallback-dev-key-crimerecord-2026")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "crime_record_management")
    
    # Session security configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)


_mongo_client = None


def get_db_client():
    """
    Get or create thread-safe singleton PyMongo MongoClient instance
    with connection pooling.
    """
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(
            Config.MONGO_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            maxPoolSize=50
        )
    return _mongo_client


def get_db():
    """
    Connect to MongoDB and return the database instance.
    Raises ConnectionFailure if the database is unreachable.
    """
    client = get_db_client()
    # Ping to check if connection is active
    client.admin.command("ping")
    return client[Config.DATABASE_NAME]


def close_db_client():
    """Close MongoClient on application shutdown."""
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
