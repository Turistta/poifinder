import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import logging

import aiohttp
import pendulum

from airflow.sensors.external_task import ExternalTaskSensor
from airflow.decorators import dag, task
from airflow.models import Variable
from common.exceptions.airflow import AirflowException

logger = logging.getLogger(__name__)


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": pendulum.yesterday(),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=15),
}


@dag(
    dag_id="request_sync_databases",
    default_args=default_args,
    description="DAG for syncing Redis and MongoDB databases",
    schedule_interval="0 */2 * * *",  # Every 2 hours
    catchup=False,
)
def sync_request():

    @task
    def request():
        """
        Trigger a sync operation between Redis and MongoDB via the FastAPI endpoint.
        """
        headers = {}
        sync_endpoint = Variable.get("FASTAPI_ENDPOINT") + "/sync"
        sync_request = {"trigger": "true"}

        async def send_request():
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(url=sync_endpoint, json=sync_request) as response:
                        if response.status != 200:
                            error = await response.text()
                            logger.warning(f"Error triggering sync operation: {error}")
                            raise AirflowException(f"Failed to send POIs. Status: {response.status}")
                        logger.info(f"Successfully sent sync request")
                except aiohttp.ClientConnectionError as e:
                    logger.error(f"Connection error for URL {sync_endpoint}: {e}")
                    raise AirflowException(f"Connection error: {e}")
                except aiohttp.ClientError as e:
                    logger.error(f"Client error for URL {sync_endpoint}: {e}")
                    raise AirflowException(f"Client error: {e}")
                except asyncio.TimeoutError:
                    logger.error(f"Request to {sync_endpoint} timed out")
                    raise AirflowException("Request timed out")

        asyncio.run(send_request())

    wait_for_find_pois = ExternalTaskSensor(
        task_id="wait_for_find_pois",
        external_dag_id="find_pois",
        timeout=300,
        allowed_states=["success"],
        mode="reschedule",
    )

    wait_for_find_pois >> request()


sync_pois_dag = sync_request()
