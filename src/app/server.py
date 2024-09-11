import logging
from contextlib import asynccontextmanager

from core.config import settings
from core.databases import MongoDBPool, RedisDBPool
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from routes import external, internal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # # Startup

    # logger.info("Starting server...")
    # redis_pool = RedisDBPool(
    #     username=settings.REDIS_USERNAME,
    #     password=settings.REDIS_PASSWORD,
    #     host=settings.REDIS_HOSTNAME,
    #     port=settings.REDIS_PORT,
    # )
    # mongo_pool = MongoDBPool(
    #     username=settings.MONGO_USERNAME,
    #     password=settings.MONGO_PASSWORD,
    #     host=settings.MONGO_HOSTNAME,
    #     port=settings.MONGO_PORT,
    #     database=settings.MONGO_DB,
    # )

    # await redis_pool.test()
    # await mongo_pool.test()

    # yield

    # logger.info("Server cleanup...")
    # await mongo_pool.close()
    # await redis_pool.close()


app = FastAPI(title="POIFinder", lifespan=lifespan)

app.include_router(internal.router)
app.include_router(external.router)


@app.get("/", include_in_schema=False)
async def redirect_docs():
    return RedirectResponse(url="/docs")
