"""Database connection management."""

import os
import asyncpg
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
db_pool = None

async def get_db_pool():
    """Get database connection pool."""
    global db_pool
    if db_pool is None and DATABASE_URL:
        try:
            db_pool = await asyncpg.create_pool(DATABASE_URL)
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return None
    return db_pool