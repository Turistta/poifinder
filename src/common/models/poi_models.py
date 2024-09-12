from datetime import datetime
from typing import Annotated, Dict, List

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from .location_models import Location


class Picture(BaseModel):
    """Picture associated with a Point of Interest."""

    url: Annotated[HttpUrl, Field(description="URL of the photo")]
    width: Annotated[int, Field(description="Width of the photo in pixels", gt=0)]
    height: Annotated[int, Field(description="Height of the photo in pixels", gt=0)]

    model_config = ConfigDict(
        json_schema_extra={"example": {"url": "https://example.com/photo.jpg", "width": 1024, "height": 768}}
    )


class Review(BaseModel):
    """Review for a Point of Interest."""

    author_name: Annotated[str, Field(default="", description="Name of the review author")]
    author_profile: Annotated[HttpUrl, Field(description="URL of the author's profile")]
    language: Annotated[str, Field(default="", description="Language in which the review is written")]
    text: Annotated[str, Field(default="", description="Text content of the review")]
    rating: Annotated[float, Field(default=0.0, description="Rating given in the review", ge=0.0, le=5.0)]
    publication_timestamp: Annotated[
        datetime, Field(default=None, description="Timestamp of when the review was published")
    ]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "author_name": "João Paulo",
                "author_profile": "https://example.com/profile/joao_paulo2o",
                "language": "pt",
                "text": "É bão, fera demais. Recomendo!",
                "rating": 4.5,
                "publication_timestamp": "2024-08-15T14:30:00Z",
            }
        }
    )


class PointOfInterest(BaseModel):
    """A Point of Interest with all its details."""

    place_id: Annotated[str, Field(description="Unique identifier for the place")]
    name: Annotated[str, Field(default="", description="Name of the place")]
    location: Annotated[Location, Field(description="Location details of the place")]
    categories: Annotated[List[str], Field(default=[], description="Categories of the place")]
    reviews: Annotated[List[Review], Field(default=[], description="List of reviews for the place")]
    pictures: Annotated[List[Picture], Field(default=[], description="List of pictures for the place")]
    ratings_total: Annotated[int, Field(description="Total number of ratings", ge=0)]
    opening_hours: Annotated[
        Dict[str, str],
        Field(
            default_factory=lambda: {
                day: "Closed" for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            },
            description="Opening hours of the place, with day names as keys",
        ),
    ]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "place_id": "ChIJN7mK3OR4XpMRbkXk5ccxbKQ",
                "name": "Parque Flamboyant",
                "location": {
                    "address": "Av. Deputado Jamel Cecílio, Goiânia - GO, 74810-100, Brasil",
                    "plus_code": "34MP+FJ Goiânia, Goiás, Brasil",
                    "coordinates": {"latitude": -16.703203, "longitude": -49.247582},
                },
                "categories": ["park", "tourist_attraction"],
                "reviews": [
                    {
                        "author_name": "João Paulo",
                        "author_profile": "https://example.com/profile/joao_paulo2o",
                        "language": "en",
                        "text": "É bão, fera demais. Recomendo!",
                        "rating": 5.0,
                        "publication_timestamp": "2024-08-15T14:30:00Z",
                    }
                ],
                "pictures": [{"url": "https://example.com/parque_flamboyant.jpg", "width": 2048, "height": 1536}],
                "ratings_total": 12000,
                "opening_hours": {
                    "Monday": "5:00 AM - 10:00 PM",
                    "Tuesday": "5:00 AM - 10:00 PM",
                    "Wednesday": "5:00 AM - 10:00 PM",
                    "Thursday": "5:00 AM - 10:00 PM",
                    "Friday": "5:00 AM - 10:00 PM",
                    "Saturday": "5:00 AM - 10:00 PM",
                    "Sunday": "5:00 AM - 10:00 PM",
                },
            }
        }
    )
