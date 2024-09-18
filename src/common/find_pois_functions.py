import logging
from typing import Any, Dict, List
import osmnx as ox
import geopandas as gpd
import asyncio
import aiohttp
from airflow.models import Variable
from common.models.poi_models import PointOfInterest
from common.exceptions.airflow import AirflowException
from math import radians, cos, sin, asin, sqrt

logger = logging.getLogger(__name__)

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    calcula a distância entre dois pontos (nao eh uma linha reta )
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371 
    return c * r * 1000  #metros
    

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

def request_pois(conf: Dict[str, Any]) -> gpd.GeoDataFrame:
        """
        Solicita POIs de uma API externa.

        Retorna:
            GeoDataFrame: GeoDataFrame contendo dados de POIs.
        """
        location = conf.get('location', {})
        lat = location.get('lat')
        lon = location.get('lon')
        radius = conf.get('radius', 1000) 
        if not lat or not lon:
            raise ValueError("Coordenadas de localização não fornecidas na configuração.")

        
        categories = conf.get('preferences', {}).get('categories', [])
        if not categories:
            categories = ['amenity', 'tourism'] 

        try:
            point = (lat, lon)
            tags = {category: True for category in categories}
            pois = ox.geometries_from_point(point, tags=tags, dist=radius)
            return pois
        except Exception as e:
            logger.error(f"Erro ao buscar POIs: {e}")
            raise AirflowException(f"Falha ao buscar POIs: {e}")

def parse_pois(pois_gdf: gpd.GeoDataFrame) -> List[PointOfInterest]:
        """
        Faz o parsing dos dados brutos de POIs em uma lista de objetos PointOfInterest.

        Args:
            pois_gdf (GeoDataFrame): GeoDataFrame contendo dados de POIs.

        Retorna:
            List[PointOfInterest]: Lista de objetos POI analisados.
        """
        try:
            pois_list = []
            for idx, row in pois_gdf.iterrows():
                poi = PointOfInterest(
                    id=row.get('osmid'),
                    name=row.get('name'),
                    category=row.get('amenity') or row.get('tourism') or row.get('shop'),
                    latitude=row.geometry.y if row.geometry else None,
                    longitude=row.geometry.x if row.geometry else None,
                    tags=row.to_dict()
                )
                pois_list.append(poi)
            return pois_list
        except Exception as e:
            logger.error(f"Erro ao analisar POIs: {e}")
            raise AirflowException(f"Falha ao analisar POIs: {e}")

def apply_filtering(parsed_pois: List[PointOfInterest], conf: Dict[str, Any]) -> List[PointOfInterest]:
        """
        Aplica o filtro baseado nas preferências do usuário aos POIs analisados.

        Args:
            parsed_pois (List[PointOfInterest]): Lista de objetos POI analisados.

        Retorna:
            List[PointOfInterest]: Lista de objetos POI filtrados.
        """
        preferences = conf.get('preferences', {})
        preferred_categories = preferences.get('categories', [])

        if not preferred_categories:
            return parsed_pois

        filtered_pois = [
            poi for poi in parsed_pois if poi.category in preferred_categories
        ]
        return filtered_pois

def process_filtered_pois(preference_filtered_pois: List[PointOfInterest], conf: Dict[str, Any]) -> List[PointOfInterest]:
        """
        Processa e ranqueia os POIs filtrados.

        Args:
            preference_filtered_pois (List[PointOfInterest]): Lista de POIs filtrados pelas preferências do usuário.

        Retorna:
            List[PointOfInterest]: Lista de objetos POI processados e ranqueados.
        """
        location = conf.get('location', {})
        user_lat = location.get('lat')
        user_lon = location.get('lon')

        if not user_lat or not user_lon:
            raise ValueError("Localização do usuário não fornecida na configuração.")

        for poi in preference_filtered_pois:
            if poi.latitude and poi.longitude:
                distance = haversine_distance(user_lat, user_lon, poi.latitude, poi.longitude)
                poi.distance = distance
            else:
                poi.distance = float('inf') 

        ranked_pois = sorted(preference_filtered_pois, key=lambda x: x.distance)
        return ranked_pois

def return_results(results: List[PointOfInterest]) -> None:
        """
        Retorna a lista final de POIs para o endpoint FastAPI.

        Args:
            results (List[PointOfInterest]): Lista final de POIs processados e ranqueados.
        """
        fastapi_endpoint = Variable.get("FASTAPI_ENDPOINT") + "/pois"
        headers = {"Content-Type": "application/json"}
        data = [poi.to_dict() for poi in results] 

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

def check_sync_trigger():
        """
        Verifica se a DAG de sincronização deve ser acionada com base no número de requisições de POI.
        """
        current_count = int(Variable.get("poi_request_count", default_var=0))
        if current_count >= 100:
            Variable.set("poi_request_count", 0)
            return True
        return False
