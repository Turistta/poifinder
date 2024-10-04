from typing import Annotated, List

from fastapi import APIRouter, Body

from common.models.airflow_models import SyncRequest, SyncResponse
from common.models.request_models import PointsOfInterestData

router = APIRouter(prefix="/internal")


# POST Send batch data structure
@router.post("/pois", tags=["pois"])
def create_batch_pois(
    request: Annotated[
        PointsOfInterestData,
        Body(),
    ],
) -> None:
    """Endpoint that receives various requests of POI generation for once."""
    pass


# POST Activate trigger mongodb/redis sync
@router.post("/sync", tags=["database"])
def sync_db_cache(request: Annotated[SyncRequest, Body()]) -> SyncResponse:
    """Endpoint triggered by Airflow scheduler that asks for FastAPI to sync its data."""
    return SyncResponse(  # TODO: Remove placeholder for testing endpoint.
        **{
            "status": "SUCCESS",
            "message": "Sync completed successfully",
            "timestamp": "2024-09-06T12:34:56Z",
            "operation_id": "12345",
        }
    )
