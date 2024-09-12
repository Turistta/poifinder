import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import logging
from typing import Any, Dict, List

import aiohttp
import pendulum
from airflow.decorators import dag, task
from airflow.models import Variable

from common.exceptions.airflow import AirflowException
from common.models.poi_models import PointOfInterest

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": pendulum.yesterday(),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": pendulum.duration(minutes=3),
}


@dag(
    dag_id="find_pois",
    default_args=default_args,
    description="DAG for filtering POIs based on user preferences and location.",
    schedule_interval=None,
    catchup=False,
)
def find_pois():
    """
    # Find POIs DAG

    This DAG is responsible for finding and filtering Points of Interest (POIs) based on user preferences and location.

    ## Tasks:
    1. load_data: Load user data and preferences
    2. request_pois: Request POIs from an external API
    3. parse_pois: Parse the raw POI data
    4. apply_filtering: Apply user preference-based filtering to POIs
    5. process_filtered_pois: Further process and rank the filtered POIs
    6. return_results: Return the final list of POIs to the user
    7. check_sync_trigger: Check if sync should be triggered
    """

    @task
    def load_data(**kwargs) -> Dict[str, Any]:
        """
        Load user data and preferences from the DAG run configuration.

        Returns:
            Dict[str, Any]: A dictionary containing user data and preferences pulled from the REST API.
        """
        # data = kwargs["dag_run"].conf
        data = {"mock_data": "test_data"}
        try:
            if not data:
                raise ValueError

            Variable.set("FASTAPI_ENDPOINT", value=os.environ["FASTAPI_ENDPOINT"])
            Variable.set("OSM_ENDPOINT", value=os.environ["OSM_ENDPOINT"])

            return data
        except ValueError:
            logger.error(msg := "No data provided in DAG run configuration")
            raise ValueError(msg)
        except KeyError:
            logger.error(msg := "No data provided in DAG run configuration")
            raise ValueError(msg)
        except Exception:
            raise

    @task
    def request_pois(conf: Dict[str, Any]) -> str:
        """
        Request POIs from an external API.

        Returns:
            str: Raw response containing POI data.
        """
        # OSMNX request

        endpoint = Variable.get("OSM_ENDPOINT")
        pass

    @task
    def parse_pois(raw_response: str) -> List[PointOfInterest]:
        """
        Parse the raw POI data into a list of PointOfInterest objects.

        Args:
            raw_response (str): Raw response from the POI API.

        Returns:
            List[PointOfInterest]: List of parsed POI objects.
        """
        # OSMNX response parsing
        pass

    @task
    def apply_filtering(parsed_pois: List[PointOfInterest], conf: Dict[str, Any]) -> List[PointOfInterest]:
        """
        Apply user preference-based filtering to the parsed POIs.

        Args:
            parsed_pois (List[PointOfInterest]): List of parsed POI objects.

        Returns:
            List[PointOfInterest]: List of filtered POI objects.
        """
        # Loading model etc, and Filtering logic?
        pass

    @task
    def process_filtered_pois(preference_filtered_pois: List[PointOfInterest]) -> List[PointOfInterest]:
        """
        Further process and rank the filtered POIs.

        Args:
            preference_filtered_pois (List[PointOfInterest]): List of POIs filtered by user preferences.

        Returns:
            List[PointOfInterest]: List of processed and ranked POI objects.
        """
        # Additional processing, such as metadata etc. # TODO: Add relevant metadata and a ranking logic.
        pass

    @task
    def return_results(results: List[PointOfInterest]) -> None:
        """
        Returns the final list of POIs to the FastAPI endpoint.

        Args:
            results (List[PointOfInterest]): Final list of processed and ranked POIs.
        """
        fastapi_endpoint = Variable.get("FASTAPI_ENDPOINT") + "/pois"
        headers = {"Content-Type": "application/json"}
        data = results  # Model dump?

        async def send_request():
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(url=fastapi_endpoint, json=data, headers=headers) as response:
                        if response.status != 200:
                            error = await response.text()
                            logger.error(
                                f"Error sending POIs to endpoint. Status: {response.status}, Response: {error}"
                            )
                            raise AirflowException(f"Failed to send POIs. Status: {response.status}")
                        logger.info(f"Successfully sent {len(results)} POIs to FastAPI")

                        current_count = int(Variable.get("poi_request_count", default_var=0))
                        Variable.set("poi_request_count", current_count + 1)
                except aiohttp.ClientConnectionError as e:
                    logger.error(f"Connection error for URL {fastapi_endpoint}: {e}")
                    raise AirflowException(f"Connection error: {e}")
                except aiohttp.ClientError as e:
                    logger.error(f"Client error for URL {fastapi_endpoint}: {e}")
                    raise AirflowException(f"Client error: {e}")
                except asyncio.TimeoutError:
                    logger.error(f"Request to {fastapi_endpoint} timed out")
                    raise AirflowException("Request timed out")

        asyncio.run(send_request())

    @task
    def check_sync_trigger():
        """
        Checks if the sync DAG should be triggered based on the number of POI requests.
        """
        current_count = int(Variable.get("poi_request_count", default_var=0))
        if current_count >= 100:
            Variable.set("poi_request_count", 0)
            from airflow.api.common.models.experimental.trigger_dag import trigger_dag

            trigger_dag("sync_databases")

    user_data = load_data()
    raw_response = request_pois(conf=user_data)
    parsed_pois = parse_pois(raw_response=raw_response)
    filtered_pois = apply_filtering(parsed_pois=parsed_pois, conf=user_data)
    processed_pois = process_filtered_pois(preference_filtered_pois=filtered_pois)
    return_results(results=processed_pois) >> check_sync_trigger()


find_pois_dag = find_pois()
