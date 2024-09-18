import os
import sys

from src.common.models.location_models import Coordinates, Location

# Adicionar o diretório de dags ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import logging
from math import asin, cos, radians, sin, sqrt
from typing import Any, Dict, List, Tuple

import aiohttp
import geopandas as gpd
import osmnx as ox
import pendulum

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
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
    This is a basic implementation and might need to be expanded based on the complexity of the data.
    """
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hours_dict = {day: "Closed" for day in days}

    if opening_hours_string:
        parts = opening_hours_string.split(";")
        for part in parts:
            if "-" in part:
                day_range, time_range = part.split(" ", 1)
                day_start, day_end = day_range.split("-")
                start_index = days.index(day_start.capitalize())
                end_index = days.index(day_end.capitalize())
                for day in days[start_index : end_index + 1]:
                    hours_dict[day] = time_range.strip()

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
    def load_data(**kwargs) -> Dict[str, Any]:
        """
        Carrega os dados e preferências do usuário da configuração da execução da DAG.

        Retorna:
            Dict[str, Any]: Um dicionário contendo dados e preferências do usuário extraídos da API REST.
        """
        data = kwargs["dag_run"].conf

        try:
            if not data:
                raise ValueError

            Variable.set("FASTAPI_ENDPOINT", value=os.environ["FASTAPI_ENDPOINT"])
            Variable.set("OSM_ENDPOINT", value=os.environ["OSM_ENDPOINT"])

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
    def request_pois(conf: Dict[str, Any]) -> gpd.GeoDataFrame:
        """
        Solicita POIs de uma API externa.

        Retorna:
            GeoDataFrame: GeoDataFrame contendo dados de POIs.
        """
        location = conf.get("location", {})
        lat = location.get("lat")
        lon = location.get("lon")
        radius = conf.get("radius", 1000)
        if not lat or not lon:
            raise ValueError("Coordenadas de localização não fornecidas na configuração.")

        categories = conf.get("preferences", {}).get("categories", [])
        if not categories:
            categories = ["amenity", "tourism"]

        try:
            point = (lat, lon)
            tags = {category: True for category in categories}
            pois = ox.geometries_from_point(point, tags=tags, dist=radius)
            return pois
        except Exception as e:
            logger.error(f"Erro ao buscar POIs: {e}")
            raise AirflowException(f"Falha ao buscar POIs: {e}")

    @task
    def parse_pois(pois_gdf: gpd.GeoDataFrame) -> List[PointOfInterest]:
        """
        Parses raw POI data from a GeoDataFrame into a list of PointOfInterest objects.
        Args:
            pois_gdf (GeoDataFrame): GeoDataFrame containing POI data.
        Returns:
            List[PointOfInterest]: List of parsed POI objects.
        """
        try:
            pois_list = []
            for _, row in pois_gdf.iterrows():
                # Extract categories
                categories = []
                for category in ["amenity", "tourism", "shop", "leisure"]:
                    if row.get(category):
                        categories.append(row[category])

                # Create location object
                location = Location(
                    address=row.get("addr:full", ""),
                    plus_code="",
                    coordinates=Coordinates(
                        latitude=row.geometry.y if row.geometry else None, # type: ignore
                        longitude=row.geometry.x if row.geometry else None, # type: ignore
                    ),
                )

                # Create POI object
                poi = PointOfInterest(
                    place_id=str(row.get("osmid", "")),
                    name=row.get("name", ""),
                    location=location,
                    categories=categories,
                    reviews=[],
                    pictures=[],
                    ratings_total=0,
                    opening_hours=parse_opening_hours(row.get("opening_hours", "")),
                )
                pois_list.append(poi)
            return pois_list
        except Exception as e:
            logger.error(f"Error parsing POIs: {e}")
            raise AirflowException(f"Failed to parse POIs: {e}")

    @task
    def apply_filtering(parsed_pois: List[PointOfInterest], conf: Dict[str, Any]) -> List[PointOfInterest]:
        """
        Applies filtering based on user preferences to the parsed POIs.
        Args:
            parsed_pois (List[PointOfInterest]): List of parsed POI objects.
            conf (Dict[str, Any]): Configuration dictionary containing user preferences.
        Returns:
            List[PointOfInterest]: List of filtered POI objects.
        """
        preferences = conf.get("preferences", {})
        preferred_categories = preferences.get("categories", [])
        if not preferred_categories:
            return parsed_pois

        filtered_pois = [
            poi for poi in parsed_pois if any(category in poi.categories for category in preferred_categories)
        ]
        return filtered_pois

    @task
    def process_filtered_pois(
        preference_filtered_pois: List[PointOfInterest], conf: Dict[str, Any]
    ) -> List[Tuple[PointOfInterest, float]]:
        """
        Processes the filtered POIs and calculates their distances from the user's location.
        Args:
            preference_filtered_pois (List[PointOfInterest]): List of POIs filtered by user preferences.
            conf (Dict[str, Any]): Configuration dictionary containing user location.
        Returns:
            List[Tuple[PointOfInterest, float]]: List of tuples containing POI objects and their distances from the user.
        """
        location = conf.get("location", {})
        user_lat = location.get("lat")
        user_lon = location.get("lon")
        if not user_lat or not user_lon:
            raise ValueError("User location not provided in configuration.")

        pois_with_distances = []
        for poi in preference_filtered_pois:
            if poi.location.coordinates.latitude and poi.location.coordinates.longitude:
                distance = haversine_distance(
                    user_lat, user_lon, poi.location.coordinates.latitude, poi.location.coordinates.longitude
                )
            else:
                distance = float("inf")
            pois_with_distances.append((poi, distance))

        ranked_pois = sorted(pois_with_distances, key=lambda x: x[1])
        return ranked_pois

    @task
    def return_results(results: List[PointOfInterest]) -> None:
        """
        Retorna a lista final de POIs para o endpoint FastAPI.

        Args:
            results (List[PointOfInterest]): Lista final de POIs processados e ranqueados.
        """
        fastapi_endpoint = Variable.get("FASTAPI_ENDPOINT") + "/pois"
        headers = {"Content-Type": "application/json"}
        data = [poi.model_dump() for poi in results]

        async def send_request():
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(url=fastapi_endpoint, json=data, headers=headers) as response:
                        if response.status != 200:
                            error = await response.text()
                            logger.error(
                                f"Erro ao enviar POIs para o endpoint. Status: {response.status}, Resposta: {error}"
                            )
                            raise AirflowException(f"Falha ao enviar POIs. Status: {response.status}")
                        logger.info(f"Enviado com sucesso {len(results)} POIs para o FastAPI")

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
    raw_response = request_pois(conf=user_data)  # type: ignore
    parsed_pois = parse_pois(raw_response)  # type: ignore
    filtered_pois = apply_filtering(parsed_pois, user_data)  # type: ignore
    processed_pois = process_filtered_pois(filtered_pois, user_data)  # type: ignore
    return_results(processed_pois) >> check_sync_trigger() >> sync_trigger  # type: ignore


find_pois_dag = find_pois()
