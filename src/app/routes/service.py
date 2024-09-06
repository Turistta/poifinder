from typing import Annotated, List

from fastapi import APIRouter, Body
from models.airflow_models import SyncRequest, SyncResponse
from models.request_models import PointsOfInterestData

router = APIRouter(prefix="/service")


# POST Send batch data structure
@router.post("/pois", tags=["pois"])
def create_batch_pois(
    request: Annotated[
        List[PointsOfInterestData],
        Body(),
    ],
) -> None:
    """Endpoint that receives various requests of POI generation for once."""
    pass


# POST Activate trigger mongodb/redis sync
@router.post("/sync", tags=["database"])
def sync_db_cache(request: Annotated[SyncRequest, Body()]) -> SyncResponse:
    """Endpoint triggered by Airflow scheduler that asks for FastAPI to sync its data."""
