import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import geopandas as gpd
import pytest
from dags.find_pois import (
    apply_filtering,
    check_sync_trigger,
    load_data,
    parse_pois,
    process_filtered_pois,
    request_pois,
)

from airflow.models import Variable
from common.models.location_models import Coordinates
from common.models.poi_models import Location, Picture, PointOfInterest, Review


@pytest.fixture
def mock_env():
    with patch.dict(
        "os.environ",
        {"FASTAPI_ENDPOINT": "http://localhost:8000", "OSM_ENDPOINT": "http://overpass-api.de/api/interpreter"},
    ):
        yield


@pytest.fixture
def sample_conf():
    return {
        "location": {"lat": -16.703203, "lon": -49.247582},
        "radius": 1000,
        "preferences": {"categories": ["park", "tourist_attraction"]},
    }


@pytest.fixture
def sample_poi():
    return PointOfInterest(
        place_id="ChIJN7mK3OR4XpMRbkXk5ccxbKQ",
        name="Parque Flamboyant",
        location=Location(
            address="Av. Deputado Jamel Cecílio, Goiânia - GO, 74810-100, Brasil",
            plus_code="34MP+FJ Goiânia, Goiás, Brasil",
            coordinates=Coordinates(latitude=-16.703203, longitude=-49.247582),
        ),
        categories=["park", "tourist_attraction"],
        reviews=[
            Review(
                author_name="João Paulo",
                author_profile="https://example.com/profile/joao_paulo2o",  # type: ignore
                language="en",
                text="É bão, fera demais. Recomendo!",
                rating=5.0,
                publication_timestamp=datetime.fromisoformat("2024-08-15T14:30:00Z"),
            )
        ],
        pictures=[Picture(url="https://example.com/parque_flamboyant.jpg", width=2048, height=1536)],
        ratings_total=12000,
        opening_hours={
            "Monday": "5:00 AM - 10:00 PM",
            "Tuesday": "5:00 AM - 10:00 PM",
            "Wednesday": "5:00 AM - 10:00 PM",
            "Thursday": "5:00 AM - 10:00 PM",
            "Friday": "5:00 AM - 10:00 PM",
            "Saturday": "5:00 AM - 10:00 PM",
            "Sunday": "5:00 AM - 10:00 PM",
        },
    )


def test_load_data(mock_env):
    kwargs = {
        "dag_run": MagicMock(
            conf={
                "location": {"lat": -16.703203, "lon": -49.247582},
                "preferences": {"categories": ["park", "tourist_attraction"]},
            }
        )
    }
    data = load_data(**kwargs)
    assert data is not None
    assert "location" in data and "preferences" in data


def test_request_pois(sample_conf):
    pois = request_pois(sample_conf)
    assert isinstance(pois, gpd.GeoDataFrame)


@patch("find_pois_functions.ox.geometries_from_point")
def test_request_pois_mocked(mock_geometries_from_point, sample_conf):
    mock_geometries_from_point.return_value = gpd.GeoDataFrame(
        {
            "osmid": ["ChIJN7mK3OR4XpMRbkXk5ccxbKQ"],
            "name": ["Parque Flamboyant"],
            "geometry": [None],
            "tourism": ["attraction"],
            "leisure": ["park"],
        }
    )
    pois = request_pois(sample_conf)
    assert isinstance(pois, gpd.GeoDataFrame)


def test_parse_pois():
    pois_gdf = gpd.GeoDataFrame(
        {
            "osmid": ["ChIJN7mK3OR4XpMRbkXk5ccxbKQ"],
            "name": ["Parque Flamboyant"],
            "geometry": [None],
            "tourism": ["attraction"],
            "leisure": ["park"],
        }
    )
    pois_list = parse_pois(pois_gdf)
    assert len(pois_list) == 1
    assert isinstance(pois_list[0], PointOfInterest)


def test_apply_filtering(sample_poi):
    filtered_pois = apply_filtering([sample_poi], {"preferences": {"categories": ["park"]}})
    assert len(filtered_pois) == 1


def test_process_filtered_pois(sample_poi):
    processed_pois = process_filtered_pois([sample_poi], {"location": {"lat": -16.703203, "lon": -49.247582}})
    assert len(processed_pois) == 1
    assert hasattr(processed_pois[0], "distance")
    assert processed_pois[0].distance == 0


@pytest.mark.asyncio
@patch("find_pois_functions.aiohttp.ClientSession.post")
async def test_request_pois(mock_post, sample_poi):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_post.return_value.__aenter__.return_value = mock_response
    await request_pois([sample_poi])
    mock_post.assert_called()


@patch.object(Variable, "get", return_value="100")
@patch.object(Variable, "set")
def test_check_sync_trigger(mock_set, mock_get):
    result = check_sync_trigger()
    assert result is True
    mock_set.assert_called_with("poi_request_count", 0)
