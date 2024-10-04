from datetime import datetime
from typing import Annotated, Any, Dict, List, Union

from pydantic import BaseModel, ConfigDict, Field

from .airflow_models import AirflowJobStatus
from .base_models import IntSeed
from .location_models import Coordinates
from .poi_models import PointOfInterest
from .preference_models import ContextConstraints, Preference


class PointOfInterestClientRequest(BaseModel):
    """The incoming Client request (query options) to be used by the PlaceDiscoveryRequest."""

    location: Annotated[Coordinates, Field(description="Geographic coordinates for the search")]
    preferences: Annotated[List[Preference], Field(min_length=1, max_length=5, description="List of user preferences")]
    max_distance: Annotated[float, Field(gt=0, le=30, description="Maximum distance (in km) to search for POIs")]
    max_results: Annotated[int, Field(default=5, gt=0, le=10, description="Maximum number of results to return")]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": {"latitude": 40.7128, "longitude": -74.0060},
                "preferences": [{"category": "restaurant", "weight": 0.8}, {"category": "museum"}],
                "max_distance": 5.0,
                "max_results": 10,
            }
        }
    )


class AirflowDagTriggerRequest(BaseModel):
    """Request for the Airflow REST API to trigger a DAG run."""

    # dag_run_id: Annotated[str, Field(description="Identifier of the DAG to trigger")]
    logical_date: Annotated[str, Field(description="Timestamp of the request")]
    conf: Annotated[PointOfInterestClientRequest, Field(description="Configuration for the DAG run")]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                # "dag_run_id": "process_poi_request",
                "logical_date": "2023-06-15T14:30:00Z",
                "conf": {
                    "location": {"latitude": 40.7128, "longitude": -74.0060},
                    "preferences": [{"category": "restaurant", "weight": 0.8}, {"category": "museum"}],
                    "max_distance": 5.0,
                    "max_results": 10,
                },
            }
        }
    )


class PointsOfInterestData(BaseModel):
    """All information related to a specific request of PointOfInterest creation."""

    seed: Annotated[IntSeed, Field()]
    conf: Annotated[Union[List[Preference], ContextConstraints], Field()]
    timestamp: Annotated[str, Field()]
    job_status: Annotated[AirflowJobStatus, Field()]
    results: Annotated[Union[List[PointOfInterest], Dict[str, Any]], Field()]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "seed": 285742,
                "config": {
                    "location": {"latitude": 40.7128, "longitude": -74.0060},
                    "preferences": [{"category": "restaurant", "weight": 0.8}, {"category": "museum"}],
                    "max_distance": 5.0,
                    "max_results": 10,
                },
                "timestamp": "2023-06-15T14:30:00Z",
                "job_status": {
                    "job_id": "550e8400e29b41d4a716446655440000",
                    "start_date": "2024-06-15T10:00:00Z",
                    "end_date": "2024-06-15T10:05:30Z",
                },
                "results": [
                    {
                        "place_id": "",
                        "name": "Hall des Lumières",
                        "location": {
                            "address": "49, Chambers Street, New York, 10007",
                            "plus_code": "",
                            "coordinates": {"latitude": 40.7137437, "longitude": -74.005072},
                        },
                        "categories": ["museum"],
                        "reviews": [],
                        "pictures": [],
                        "ratings_total": 0,
                        "opening_hours": {
                            "Monday": "0:00 AM - 23:59 PM",
                            "Tuesday": "0:00 AM - 23:59 PM",
                            "Wednesday": "0:00 AM - 23:59 PM",
                            "Thursday": "0:00 AM - 23:59 PM",
                            "Friday": "0:00 AM - 23:59 PM",
                            "Saturday": "0:00 AM - 23:59 PM",
                            "Sunday": "0:00 AM - 23:59 PM",
                        },
                    },
                    {
                        "place_id": "",
                        "name": "Temple Room",
                        "location": {
                            "address": "Unknown",
                            "plus_code": "",
                            "coordinates": {"latitude": 40.7113229, "longitude": -74.0067467},
                        },
                        "categories": ["restaurant"],
                        "reviews": [],
                        "pictures": [],
                        "ratings_total": 0,
                        "opening_hours": {
                            "Monday": "0:00 AM - 23:59 PM",
                            "Tuesday": "0:00 AM - 23:59 PM",
                            "Wednesday": "0:00 AM - 23:59 PM",
                            "Thursday": "0:00 AM - 23:59 PM",
                            "Friday": "0:00 AM - 23:59 PM",
                            "Saturday": "0:00 AM - 23:59 PM",
                            "Sunday": "0:00 AM - 23:59 PM",
                        },
                    },
                ],
            }
        }
    )
