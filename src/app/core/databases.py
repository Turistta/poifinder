import logging
from typing import Optional

import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure

from app.repositories.abstract_repository import AbstractDatabase

logger = logging.getLogger(__name__)


class MongoDBPool(AbstractDatabase):
    def __init__(self, username: str, password: str, host: str, port: int, database: str):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.client: Optional[AsyncIOMotorClient] = None

    async def test(self):
        if not self.client:
            endpoint = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
            self.client = AsyncIOMotorClient(endpoint)
            try:
                await self.client.admin.command("ping")
                logger.info("Connected to MongoDB server.")
            except ConnectionFailure as e:
                logger.error(f"Couldn't connect to MongoDB server: {e}")
                self.client = None
                raise e

    async def close(self):
        if self.client:
            self.client.close()
            self.client = None
            logger.info("MongoDB connection closed.")


class RedisDBPool(AbstractDatabase):
    def __init__(self, username: str, password: str, host: str, port: int):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.redis_pool: Optional[redis.ConnectionPool] = None

    async def test(self):
        if not self.redis_pool:
            endpoint = f"redis://{self.username}:{self.password}@{self.host}:{self.port}"
            self.redis_pool = redis.ConnectionPool.from_url(endpoint)
            try:
                client = redis.Redis(connection_pool=self.redis_pool)
                await client.ping()
                logger.info("Connected to Redis cluster.")
            except (ConnectionError, ConnectionRefusedError) as e:
                logger.error(f"Couldn't connect to Redis cluster: {e}")
                self.redis_pool = None
                raise e

    async def close(self):
        if self.redis_pool:
            await self.redis_pool.aclose()
            logger.info("Redis connection closed.")
