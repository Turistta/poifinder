from datetime import datetime
from enum import Enum
from typing import Annotated, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

# Airflow


class AirflowJobStatus(str, Enum):
    """The possible states of an [Airflow] job."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Utils


class Coordinates(BaseModel):
    """Geographic coordinates."""

    latitude: Annotated[float, Field(ge=-90, le=90, description="Latitude in decimal degrees")]
    longitude: Annotated[float, Field(ge=-180, le=180, description="Longitude in decimal degrees")]


class UserPreference(BaseModel):
    """User's preference for a specific category."""

    category: Annotated[str, Field(min_length=1, max_length=100)]
    weight: Annotated[Optional[float], Field(ge=0, le=1)]  # Not using, for now.


class POIFinderRequest(BaseModel):
    """The incoming request to the FastAPI service for finding POIs."""

    user_id: Annotated[str, Field(min_length=1, max_length=50)]
    location: Coordinates
    preferences: Annotated[List[UserPreference], Field(min_length=1, max_length=10)]
    max_distance: Annotated[float, Field(gt=0, le=30)]
    max_results: Annotated[int, Field(default=10, gt=0, le=25)]

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "user_id": "user123",
                    "location": {"latitude": 40.7128, "longitude": -74.0060},
                    "preferences": [{"category": "restaurant", "weight": 0.8}, {"category": "museum"}],
                    "max_distance": 5.0,
                    "max_results": 15,
                }
            ]
        }


class POIFinderResponse(BaseModel):
    """The initial response from the FastAPI service after job submission."""

    job_id: Annotated[str, Field(min_length=1, max_length=50)]
    status: AirflowJobStatus
    submitted_at: Annotated[datetime, Field(description="UTC timestamp of job submission")]
    estimated_completion_time: Optional[
        Annotated[datetime, Field(description="Estimated UTC timestamp of job completion")]
    ]

    class Config:
        schema_extra = {
            "example": {
                "job_id": "76",
                "status": "PROCESSING",
                "submitted_at": "2023-09-04T12:00:00Z",
                "estimated_completion_time": "2023-09-04T12:01:00Z",
            }
        }


# POI models


class Location(BaseModel):
    """Detailed location of a Point of Interest."""

    address: Annotated[str, Field(default="")]
    plus_code: Annotated[str, Field(default="")]
    coordinates: Annotated[Coordinates, Field(...)]


class Picture(BaseModel):
    """Picture associated with a Point of Interest."""

    url: Annotated[HttpUrl, Field(description="URL of the photo.")]
    width: Annotated[int, Field(description="Width of the photo in pixels.", gt=0)]
    height: Annotated[int, Field(description="Height of the photo in pixels.", gt=0)]


class Review(BaseModel):
    """Review for a Point of Interest."""

    author_name: Annotated[str, Field(default="", description="Name of the review author.")]
    author_profile: Annotated[HttpUrl, Field(description="URL of the author's profile.")]
    language: Annotated[str, Field(default="", description="Language in which the review is written.")]
    text: Annotated[str, Field(default="", description="Text content of the review.")]
    rating: Annotated[
        float, Field(default=0.0, description="Rating given in the review, between 0.0 and 5.0.", ge=0.0, le=5.0)
    ]
    publication_timestamp: Annotated[
        datetime, Field(default=None, description="Timestamp of when the review was published.")
    ]


class PointOfInterest(BaseModel):
    """A Point of Interest with all its details."""

    place_id: Annotated[str, Field(description="Unique identifier for the place.")]
    name: Annotated[str, Field(default="", description="Name of the place.")]
    location: Annotated[Location, Field(description="Location details of the place.")]
    categories: Annotated[List[str], Field(default=[], description="Category of amenity of the place.")]
    reviews: Annotated[List[Review], Field(default=[], description="List of reviews for the place.")]
    pictures: Annotated[List[Picture], Field(default=[], description="List of pictures for the place.")]
    ratings_total: Annotated[int, Field(description="Total number of ratings.", ge=0)]
    opening_hours: Annotated[
        dict[str, str],
        Field(
            default_factory=lambda: {
                day: "Closed" for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            },
            description="Opening hours of the place, with day names as keys.",
        ),
    ]


class POIFinderResult(BaseModel):
    """Final result of a POI finding job."""

    job_id: Annotated[UUID, Field(min_length=1, max_length=50)]
    user_id: Annotated[str, Field(min_length=1, max_length=50)]
    points_of_interest: Annotated[List[PointOfInterest], Field(max_length=25)]
    created_at: Annotated[datetime, Field(description="UTC timestamp of result creation")]


class POIFinderJobQuery(BaseModel):
    """Query to check the status of a POI finding job."""

    job_id: Annotated[UUID, Field(min_length=1, max_length=50)]

    class Config:
        schema_extra = {"example": {"job_id": "76"}}


class PlaceDiscoveryRequest(BaseModel):
    """Request to the third-party API service for discovering places."""

    location: Annotated[
        Coordinates, Field(..., description="Latitude and longitude where to retrieve place information.")
    ]
    max_distance: Annotated[float, Field(..., description="Distance (in meters) within which to return place results.")]
    language: Annotated[Optional[str], Field(default="en", description="The language in which to return results.")]
    place_types: Annotated[
        Optional[List[str]], Field(None, description="Restricts results to places matching the specified type.")
    ]

    class Config:
        schema_extra = {
            "example": {
                "location": {"latitude": 40.7128, "longitude": -74.0060},
                "max_distance": 1000,
                "language": "en",
                "place_types": [["restaurant", "cafe"], ["bar"]],
            }
        }


class FilterRequest(BaseModel):
    """Request to filter discovered POIs based on user preferences."""

    discovered_pois: Annotated[List[PointOfInterest], Field(min_length=1, max_length=100)]
    user_preferences: Annotated[List[UserPreference], Field(min_length=1, max_length=10)]


class AirflowDAGConf(POIFinderRequest):
    """Configuration for the Airflow DAG, combining necessary information from Request and additional fields."""

    job_id: Annotated[int, Field(min_length=1, max_length=50, description="Unique identifier for the job")]
