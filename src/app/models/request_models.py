from datetime import datetime
from typing import Annotated, Any, Dict, List, Union

from models.airflow_models import AirflowJobStatus
from models.base_models import IntSeed
from models.location_models import Coordinates
from models.poi_models import PointOfInterest
from models.preference_models import ContextConstraints, Preference
from pydantic import BaseModel, ConfigDict, Field


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

    dag_id: Annotated[str, Field(description="Identifier of the DAG to trigger")]
    request_date: Annotated[datetime, Field(description="Timestamp of the request")]
    config: Annotated[PointOfInterestClientRequest, Field(description="Configuration for the DAG run")]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dag_id": "process_poi_request",
                "request_date": "2023-06-15T14:30:00Z",
                "config": {
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
    config: Annotated[Union[List[Preference], ContextConstraints], Field()]
    timestamp: Annotated[datetime, Field()]
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
            }
        }
    )