import logging
from typing import Annotated, Union

from fastapi import Body, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasicCredentials

from middleware import auth_user, get_job_response, retrieve_results, trigger_dag_run
from models.models import AirflowJobStatus, POIFinderRequest, POIFinderResults

logger = logging.getLogger(__name__)

app = FastAPI(title="POIFinder")


@app.post("/find_pois", response_model=Union[POIFinderResults, AirflowJobStatus])
async def find_pois(
    request: Annotated[POIFinderRequest, Body()],
    credentials: Annotated[HTTPBasicCredentials, Depends(auth_user)],
):
    try:
        existing_job = await get_job_response(request.user_id)
        if isinstance(existing_job, AirflowJobStatus):
            if existing_job.status == "SUCCESS":
                return await retrieve_results(request.user_id)
            return existing_job
        new_job_status = await trigger_dag_run(request, "poi_finder", credentials)  # type: ignore
        return new_job_status

    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
