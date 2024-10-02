from datetime import datetime
from typing import Annotated

import aiohttp
import json
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from services.airflow_service import AirflowService, get_airflow_service
import random
import string

from common.models.airflow_models import AirflowJobStatus
from common.models.base_models import HexUUIDString
from common.models.request_models import (
    AirflowDagTriggerRequest,
    PointOfInterestClientRequest,
    PointsOfInterestData,
)

router = APIRouter(prefix="/external")


# GET Query POIs
@router.get("/pois", tags=["pois"])
def get_pois_data(poi_data_hash: Annotated[HexUUIDString, Query()]) -> PointsOfInterestData:
    pass


@router.post("/pois", tags=["pois"])
async def create_pois(
    request: Annotated[PointOfInterestClientRequest, Body()],
    airflow_service: Annotated[AirflowService, Depends(get_airflow_service)],
) -> AirflowJobStatus:
    #s = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    dag_run_data_dict = AirflowDagTriggerRequest(
        #dag_run_id=s, 
        logical_date = datetime.now().replace(microsecond=0).isoformat() + 'Z', 
        conf=request.model_dump()
    ).model_dump()
    #dag_run_data_str = json.dumps(dag_run_data_dict)

    try:
        dag_run = await airflow_service.trigger_dag("find_pois", dag_run_data_dict)
    except aiohttp.ClientResponseError as e:
        raise HTTPException(status_code=e.status, detail=f"Failed to trigger DAG: {e.message}")

    return AirflowJobStatus(
        job_id=dag_run["dag_run_id"],
        start_date=dag_run["start_date"],
        end_date=dag_run.get("end_date"),
        state=dag_run["state"],
    )


@router.get("/job", tags=["jobs"])
async def get_job(
    job_id: Annotated[str, Query()], airflow_service: Annotated[AirflowService, Depends(get_airflow_service)]
) -> AirflowJobStatus:
    try:
        dag_run = await airflow_service.get_dag_run("find_pois", job_id)
    except aiohttp.ClientResponseError as e:
        raise HTTPException(status_code=e.status, detail=f"Failed to get job status: {e.message}")

    return AirflowJobStatus(
        job_id=dag_run["dag_run_id"],
        start_date=dag_run["start_date"],
        end_date=dag_run.get("end_date"),
        state=dag_run["state"],
    )
