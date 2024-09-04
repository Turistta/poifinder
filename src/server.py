import logging
from datetime import datetime, timedelta
from typing import Annotated
from uuid import uuid4

import aiohttp
from fastapi import BackgroundTasks, Body, FastAPI

from config import settings
from models.models import (
    AirflowDAGConf,
    AirflowJobStatus,
    POIFinderRequest,
    POIFinderResponse,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="POIFinder")


@app.post("/find_pois", response_model=POIFinderResponse)
async def find_pois(
    request: POIFinderRequest,  # type: ignore
    background_tasks: BackgroundTasks,
):
    pass


@app.get("/job_status/{job_id}", response_model=POIFinderResponse)
async def get_job_status(job_id: str):
    pass
