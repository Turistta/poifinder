import datetime
import json
import os
import random
import sys
import tempfile

from shapely import Point, Polygon

# Adicionar o diretório de dags ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import logging
import time
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from typing import Any, Dict, List, Tuple

import aiohttp
import geopandas as gpd
import osmnx as ox
import pendulum

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.python import get_current_context
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from common.exceptions.airflow import AirflowException
from common.models.airflow_models import AirflowJobStatus
from common.models.location_models import Coordinates, Location
from common.models.poi_models import PointOfInterest
from common.models.request_models import PointsOfInterestData

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

seed_value = int(time.time()) % 100000
random.seed(seed_value)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    calcula a distância entre dois pontos (nao eh uma linha reta )
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r * 1000  # metros


def parse_opening_hours(opening_hours_string: str) -> Dict[str, str]:
    """
    Parses the OpenStreetMap opening_hours string into a dictionary.
    Assumes English input.
    """
    full_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    short_days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    hours_dict = {
        day: "0:00 AM - 23:59 PM"
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    }

    if not opening_hours_string:
        return hours_dict

    try:
        parts = opening_hours_string.split(";")
        for part in parts:
            part = part.strip()
            if not part:
                continue

            if part.lower().startswith(("mo-su", "all days", "daily", "everyday")):
                time_range = part.split(" ", 1)[1] if " " in part else "24/7"
                for day in full_days:
                    hours_dict[day] = time_range.strip()
                continue

            if " " in part:
                day_range, time_range = part.split(" ", 1)
            else:
                day_range, time_range = part, "24/7"

            if "-" in day_range:
                day_start, day_end = day_range.split("-")
                start_index = short_days.index(day_start[:2].capitalize())
                end_index = short_days.index(day_end[:2].capitalize())
                current_days = full_days[start_index : end_index + 1]
            else:
                current_days = [full_days[short_days.index(day_range[:2].capitalize())]]
            for day in current_days:
                hours_dict[day] = time_range.strip()
            return hours_dict
    except:
        return hours_dict


@dag(
    dag_id="find_pois",
    default_args=default_args,
    description="DAG para filtrar POIs com base nas preferências do usuário e localização.",
    schedule_interval=None,
    catchup=False,
)
def find_pois():
    @task
    def load_data(**kwargs) -> dict[str, Any]:
        """
        Carrega os dados e preferências do usuário da configuração da execução da DAG.

        Retorna:
            Dict[str, Any]: Um dicionário contendo dados e preferências do usuário extraídos da API REST.
        """
        data = kwargs["dag_run"].conf
        data = {
            "location": {"latitude": 40.7128, "longitude": -74.006},
            "maxDistance": 5,
            "maxResults": 10,
            "preferences": [{"category": "restaurant", "weight": 0.8}, {"category": "museum", "weight": None}],
        }

        try:
            if not data:
                raise ValueError

            Variable.set("FASTAPI_ENDPOINT", value=os.environ["FASTAPI_ENDPOINT"])

            return data
        except ValueError:
            logger.error(msg := "Nenhum dado fornecido na configuração da execução da DAG")
            raise ValueError(msg)
        except KeyError:
            logger.error(msg := "Variáveis de ambiente não definidas")
            raise ValueError(msg)
        except Exception as e:
            logger.error(f"Erro desconhecido: {e}")
            raise

    @task
    def request_pois(conf: dict[str, Any]) -> str:
        """
        Solicita POIs de uma API externa.

        Retorna:
            GeoDataFrame: GeoDataFrame contendo dados de POIs.
        """
        location = conf.get("location", {})
        latitude = location.get("latitude")
        longitude = location.get("longitude")
        radius = conf.get("radius", 1000)
        if not latitude or not longitude:
            raise ValueError("Coordenadas de localização não fornecidas na configuração.")

        categories = []
        for item in conf.get("preferences", []):
            if isinstance(item, dict):
                categories.extend(item.get("categories", []))

        if not categories:
            categories = ["amenity", "tourism"]

        try:
            point = (latitude, longitude)
            tags = {category: True for category in categories}

            pois = ox.geometries_from_point(point, tags=tags, dist=radius).to_json()

            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
                temp_file.write(pois)
                temp_file_path = temp_file.name

            return temp_file_path
        except Exception as e:
            logger.error(f"Erro ao buscar POIs: {e}")
            raise AirflowException(f"Falha ao buscar POIs: {e}")

    @task
    def parse_pois(pois_file: str) -> str:
        """
        Parses raw POI data from a file into a list of PointOfInterest objects.
        Args:
            pois_file (str): Path to the file containing raw POI data.
        Returns:
            str: Path to the file containing parsed POI objects.
        """

        print("KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK")
        with open(pois_file, "r") as f:
            pois_json = json.load(f)
        pois_gdf = gpd.GeoDataFrame.from_features(pois_json)

        try:
            pois_list = []
            for _, row in pois_gdf.iterrows():
                # Extract categories
                categories = []
                for category in ["amenity", "tourism", "shop", "leisure"]:
                    if row.get(category):
                        categories.append(row[category])
                
                print("O erro nessa bosta é aqui kkkkkkkkkkkkkkkkkkkkk")
                end = row.get("addr:full")
                if end is None or end != end:
                    end = ""
                else:
                    end = str(end)

<<<<<<< Updated upstream
                # Construct address from available tags
                address_parts = []
                for addr_tag in ["addr:housenumber", "addr:street", "addr:city", "addr:postcode"]:
                    if row.get(addr_tag):
                        address_parts.append(str(row[addr_tag]))
                address = ", ".join(address_parts) if address_parts else "Unknown"

                if isinstance(row.geometry, Point):
                    coords = Coordinates(
                        latitude=row.geometry.y,
                        longitude=row.geometry.x,
                    )
                elif isinstance(row.geometry, Polygon):
                    # Use the centroid for the polygon
                    centroid = row.geometry.centroid
                    coords = Coordinates(
                        latitude=centroid.y,
                        longitude=centroid.x,
                    )
                else:
                    coords = Coordinates(latitude=0, longitude=0)

                location = Location(address=address, plus_code="", coordinates=coords)

                # Handle potentially None values
                name = row.get("name") or "Unnamed Location"
                place_id = str(row.get("osmid") or "")
=======
                address=row.get("addr:full")
                print(address)
                print("O erro é no end kkkkkkkkkkkkkkkkkkkkkkkkkkkkk")
                print(row)
                # Create location object
                location = Location(
                    address=end,
                    plus_code="",
                    coordinates=Coordinates(
                        latitude=row.geometry.y if row.geometry else None,
                        longitude=row.geometry.x if row.geometry else None,
                    ),
                )
>>>>>>> Stashed changes

                # Create POI object
                poi = PointOfInterest(
                    place_id=place_id,
                    name=name,
                    location=location,
                    categories=categories,
                    reviews=[],
                    pictures=[],
                    ratings_total=0,
                    opening_hours=parse_opening_hours(row.get("opening_hours", "")),
                )
                pois_list.append(poi)

            # Write parsed POIs to a temporary file
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
                json.dump([poi.model_dump() for poi in pois_list], temp_file)
                temp_file_path = temp_file.name
            return temp_file_path
        except Exception as e:
            logger.warning(f"Error parsing POIs: {e}")
            raise AirflowException(f"Failed to parse POIs: {e}")

    @task
    def apply_filtering(parsed_pois_file: str, conf: dict[str, Any]) -> str:
        """
        Applies filtering based on user preferences to the parsed POIs.

        Args:
            parsed_pois_file (str): Path to the file containing parsed POI objects.
            conf_file (str): Path to the configuration file.

        Returns:
            str: Path to the file containing filtered POI objects.
        """
        with open(parsed_pois_file, "r") as f:
            parsed_pois = [PointOfInterest(**poi) for poi in json.load(f)]

        preferences = conf.get("preferences", {})
        preferred_categories = [pref["category"] for pref in preferences]
        if not preferred_categories:
            filtered_pois = parsed_pois
        else:
            filtered_pois = [
                poi for poi in parsed_pois if any(category in poi.categories for category in preferred_categories)
            ]

        # Write filtered POIs to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            json.dump([poi.model_dump() for poi in filtered_pois], temp_file)
            temp_file_path = temp_file.name

        return temp_file_path

    @task
    def process_filtered_pois(filtered_pois_file: str, conf: dict[str, Any]) -> str:
        """
        Processes the filtered POIs and calculates their distances from the user's location.

        Args:
            filtered_pois_file (str): Path to the file containing filtered POI objects.
            conf_file (str): Path to the configuration file.

        Returns:
            str: Path to the file containing processed POI objects with distances.
        """
        with open(filtered_pois_file, "r") as f:
            filtered_pois = [PointOfInterest(**poi) for poi in json.load(f)]

        location = conf.get("location", {})
        user_lat = location.get("latitude")
        user_lon = location.get("longitude")
        if not user_lat or not user_lon:
            raise ValueError("User location not provided in configuration.")

        pois_with_distances = []
        for poi in filtered_pois:
            if poi.location.coordinates.latitude and poi.location.coordinates.longitude:
                distance = haversine_distance(
                    user_lat, user_lon, poi.location.coordinates.latitude, poi.location.coordinates.longitude
                )
            else:
                distance = float("inf")
            pois_with_distances.append((poi, distance))

        ranked_pois = sorted(pois_with_distances, key=lambda x: x[1])

        # Write processed POIs to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            json.dump([(poi.model_dump(), distance) for poi, distance in ranked_pois], temp_file)
            temp_file_path = temp_file.name

        return temp_file_path

    @task
    def return_results(results_file: str, conf: dict[str, Any]) -> None:
        """
        Retorna a lista final de POIs para o endpoint FastAPI.

        Args:
            results_file (str): Path to the file containing final processed POIs.
        """
        with open(results_file, "r") as f:
            results = json.load(f)

        fastapi_endpoint = Variable.get("FASTAPI_ENDPOINT") + "/pois"
        headers = {"Content-Type": "application/json"}

        context = get_current_context()
        job_status = AirflowJobStatus(
            job_id=context["dag_run"].run_id,
            start_date=context["dag_run"].start_date.isoformat(),
            end_date=str(datetime.now().isoformat()),
            state="SUCCESS",
        )
        data = PointsOfInterestData(
            seed=seed_value,
            conf=conf["preferences"],
            timestamp=datetime.now().isoformat(),
            job_status=job_status,
            results=[poi for poi, _ in results],
        )

        async def send_request():
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(url=fastapi_endpoint, json=data.model_dump(), headers=headers) as response:
                        if response.status != 200:
                            error = await response.text()
                            logger.error(
                                f"Erro ao enviar POIs para o endpoint. Status: {response.status}, Resposta: {error}"
                            )
                            raise AirflowException(f"Falha ao enviar POIs. Status: {response.status}")
                        logger.info(f"Enviados {len(results)} POIs para o endpoint")
                        current_count = int(Variable.get("poi_request_count", default_var=0))
                        Variable.set("poi_request_count", current_count + 1)
                except aiohttp.ClientConnectionError as e:
                    logger.error(f"Erro de conexão para a URL {fastapi_endpoint}: {e}")
                    raise AirflowException(f"Erro de conexão: {e}")
                except aiohttp.ClientError as e:
                    logger.error(f"Erro do cliente para a URL {fastapi_endpoint}: {e}")
                    raise AirflowException(f"Erro do cliente: {e}")
                except asyncio.TimeoutError:
                    logger.error(f"Requisição para {fastapi_endpoint} expirou")
                    raise AirflowException("Requisição expirou")

        asyncio.run(send_request())

    @task
    def check_sync_trigger() -> bool:
        """
        Verifica se a DAG de sincronização deve ser acionada com base no número de requisições de POI.
        """
        current_count = int(Variable.get("poi_request_count", default_var=0))
        if current_count >= 100:
            Variable.set("poi_request_count", 0)
            return True
        return False

    sync_trigger = TriggerDagRunOperator(
        task_id="sync_trigger",
        trigger_dag_id="sync_pois",
    )

    user_data = load_data()
    raw_response_file = request_pois(conf=user_data)
    parsed_pois_file = parse_pois(pois_file=raw_response_file)
    filtered_pois_file = apply_filtering(parsed_pois_file=parsed_pois_file, conf=user_data)
    processed_pois_file = process_filtered_pois(filtered_pois_file=filtered_pois_file, conf=user_data)
    return_results(results_file=processed_pois_file, conf=user_data) >> check_sync_trigger() >> sync_trigger


find_pois_dag = find_pois()
