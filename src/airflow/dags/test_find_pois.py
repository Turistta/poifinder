import pytest
from unittest.mock import patch, MagicMock
from airflow.models import Variable
from common.find_pois_functions import (
    load_data,
    request_pois,
    parse_pois,
    apply_filtering,
    process_filtered_pois,
    return_results,
    check_sync_trigger,
    haversine_distance
)
from common.models.poi_models import PointOfInterest


def test_load_data():
    # mock das variaveis de ambiente
    with patch.dict('os.environ', {'FASTAPI_ENDPOINT': 'http://localhost:8000', 'OSM_ENDPOINT': 'http://overpass-api.de/api/interpreter'}):
        kwargs = {'dag_run': MagicMock(conf={'location': {'lat': 40.7128, 'lon': -74.0060}, 'preferences': {'categories': ['amenity', 'shop']}})}
        data = load_data(**kwargs)
        assert data is not None
        assert 'location' in data
        assert 'preferences' in data


def test_request_pois():
    conf = {'location': {'lat': 40.7128, 'lon': -74.0060}, 'radius': 1000, 'preferences': {'categories': ['amenity', 'shop']}}
    pois = request_pois(conf)
    assert pois is not None
    assert isinstance(pois, gpd.GeoDataFrame)


@patch('find_pois_functions.ox.geometries_from_point')
def test_request_pois(mock_geometries_from_point):
    mock_geometries_from_point.return_value = gpd.GeoDataFrame({'osmid': [1], 'name': ['Test POI'], 'geometry': [None]})
    conf = {'location': {'lat': 40.7128, 'lon': -74.0060}, 'radius': 1000, 'preferences': {'categories': ['amenity', 'shop']}}
    pois = request_pois(conf)
    assert pois is not None
    assert isinstance(pois, gpd.GeoDataFrame)


def test_parse_pois():
    pois_gdf = gpd.GeoDataFrame({
        'osmid': [1],
        'name': ['Test POI'],
        'amenity': ['cafe'],
        'geometry': [None]
    })
    pois_list = parse_pois(pois_gdf)
    assert len(pois_list) == 1
    assert isinstance(pois_list[0], PointOfInterest)


def test_apply_filtering():
    pois_list = [
        PointOfInterest(id=1, name='Cafe', category='cafe', latitude=40.7128, longitude=-74.0060, tags={})
    ]
    conf = {'preferences': {'categories': ['cafe']}}
    filtered_pois = apply_filtering(pois_list, conf)
    assert len(filtered_pois) == 1


def test_process_filtered_pois():
    pois_list = [
        PointOfInterest(id=1, name='Cafe', category='cafe', latitude=40.7128, longitude=-74.0060, tags={})
    ]
    conf = {'location': {'lat': 40.7128, 'lon': -74.0060}}
    processed_pois = process_filtered_pois(pois_list, conf)
    assert len(processed_pois) == 1
    assert hasattr(processed_pois[0], 'distance')
    assert processed_pois[0].distance == 0


@pytest.mark.asyncio
@patch('find_pois_functions.aiohttp.ClientSession.post')
async def test_return_results(mock_post):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_post.return_value.__aenter__.return_value = mock_response

    pois_list = [
        PointOfInterest(id=1, name='Cafe', category='cafe', latitude=40.7128, longitude=-74.0060, tags={}, distance=0)
    ]

    await return_results(pois_list)
    mock_post.assert_called()


def test_check_sync_trigger():
    with patch.object(Variable, 'get', return_value='100'):
        with patch.object(Variable, 'set') as mock_set:
            result = check_sync_trigger()
            assert result is True
            mock_set.assert_called_with('poi_request_count', 0)
