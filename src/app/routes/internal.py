from typing import Annotated

from fastapi import APIRouter, Body, Query
from models.airflow_models import AirflowJobStatus
from models.base_models import HexUUIDString
from models.request_models import PointOfInterestClientRequest, PointsOfInterestData

router = APIRouter(prefix="/external")


# GET Query POIs
@router.get("/pois", tags=["pois"])
def get_pois_data(poi_data_hash: Annotated[HexUUIDString, Query()]) -> PointsOfInterestData:
    pass


# POST Create POIs
@router.post("/pois", tags=["pois"])
def create_pois(
    request: Annotated[PointOfInterestClientRequest, Body()],
) -> AirflowJobStatus:
    pass


# GET Query JobStatus
@router.get("/job", tags=["jobs"])
def get_job(job_id: Annotated[HexUUIDString, Query()]) -> AirflowJobStatus:
    pass
