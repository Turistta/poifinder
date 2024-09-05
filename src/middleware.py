import logging
import secrets
from datetime import datetime, timedelta
from pprint import pprint
from typing import Annotated, Optional

import aiohttp
from aiohttp import BasicAuth, ClientConnectionError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config import settings
from models.models import AirflowJobStatus, POIFinderRequest, POIFinderResults

security = HTTPBasic()


logger = logging.getLogger(__name__)


class AirflowException(Exception):
    pass


class NoJobsFoundException(Exception):
    pass


class FakeDB:
    def __init__(self):
        self.user_jobs: dict[str, AirflowJobStatus] = {}
        self.user_results: dict[str, POIFinderResults] = {}

    async def save_job(self, user_id: str, job_status: AirflowJobStatus) -> None:
        self.user_jobs[user_id] = job_status

    async def get_job_status(self, user_id: str) -> Optional[AirflowJobStatus]:
        return self.user_jobs.get(user_id)

    async def save_results(self, user_id: str, results: POIFinderResults) -> None:
        self.user_results[user_id] = results

    async def get_results(self, user_id: str) -> Optional[POIFinderResults]:
        return self.user_results.get(user_id)


db = FakeDB()

# Auth


def auth_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
) -> HTTPBasicCredentials:
    username = credentials.username.encode("utf-8")
    password = credentials.password.encode("utf-8")
    auth_user = bytes(settings.airflow_username, encoding="utf-8")  # type: ignore
    auth_password = bytes(settings.airflow_password, encoding="utf-8")  # type: ignore
    is_correct_user = secrets.compare_digest(username, auth_user)
    is_correct_password = secrets.compare_digest(password, auth_password)
    if not (is_correct_user and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


# Airflow


async def trigger_dag_run(
    request: POIFinderRequest, dag_id: str, credentials: HTTPBasicCredentials
) -> AirflowJobStatus:
    endpoint = settings.airflow_api_endpoint + "/dags/{dag_id}/dagRuns".format(dag_id=dag_id)  # type: ignore
    airflow_credentials = BasicAuth(login=credentials.username, password=credentials.password, encoding="utf-8")
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    payload = {"conf": request.model_dump(mode="json")}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url=endpoint, headers=headers, json=payload, auth=airflow_credentials) as response:
                if response.status == status.HTTP_200_OK:
                    content = await response.json()
                    job_status = AirflowJobStatus(
                        job_id=content["dag_run_id"],
                        status=content["state"].upper(),
                        submitted_at=datetime.fromisoformat(content["data_interval_start"]),
                        estimated_completion_time=datetime.now() + timedelta(minutes=5),
                    )
                    try:
                        await save_job(request.user_id, job_status)
                    except Exception as e:
                        raise e
                    return job_status
                logger.error(msg := f"{__name__} raised for status: {response.status}")
                raise AirflowException(msg)
        except ClientConnectionError as e:
            logger.error(msg := f"Request error for {endpoint}: {e}")
            raise


async def save_job(user_id: str, job_status: AirflowJobStatus) -> None:
    try:
        await db.save_job(user_id, job_status)
    except Exception as e:
        raise e


async def get_job_response(user_id: str) -> Optional[AirflowJobStatus]:
    job_status = await db.get_job_status(user_id)
    try:
        if job_status is None:
            raise NoJobsFoundException(f"No job found for user {user_id}")
        else:
            return job_status
    except NoJobsFoundException as e:
        logger.info(e)
        return None


async def retrieve_results(user_id: str) -> POIFinderResults:
    try:
        results = await db.get_results(user_id)
        if results is None:
            raise ValueError(f"No results found for user {user_id}")
        return results
    except Exception as e:
        raise e
