from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class Coordinates(BaseModel):
    """Geographic coordinates."""

    latitude: Annotated[float, Field(ge=-90, le=90, description="Latitude in decimal degrees")]
    longitude: Annotated[float, Field(ge=-180, le=180, description="Longitude in decimal degrees")]

    model_config = ConfigDict(json_schema_extra={"example": {"latitude": -17.7339, "longitude": -49.1236}})


class Location(BaseModel):
    """Detailed location of a Point of Interest."""

    address: Annotated[str, Field(default="", description="Street address of the location")]
    plus_code: Annotated[str, Field(default="", description="Google Plus Code of the location")]
    coordinates: Annotated[Coordinates, Field(..., description="Geographic coordinates of the location")]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "address": "Cristo Redentor, Morrinhos - State of Goiás, 75650-000",
                "plus_code": "7V8H+CH",
                "coordinates": {"latitude": -17.7339, "longitude": -49.1236},
            }
        }
    )
