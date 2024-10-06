from typing import Annotated, Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class Preference(BaseModel):
    """User preference for a specific category of Points of Interest."""

    category: Annotated[str, Field(min_length=3, max_length=25, description="Category of interest")]
    weight: Annotated[
        Optional[float], Field(ge=0, le=1, default=None, description="Weight of preference, if specified")
    ]

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"category": "restaurant", "weight": 0.8}, {"category": "museum"}]},
    )


class ContextConstraints(BaseModel):
    """Filters on POIs selection selected by the Service."""

    constraint: Annotated[Dict[str, Any], Field()]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"extra_config": {"foo": "bar"}}, {"not_a_config": [{"not": "real"}, {"value": "example"}]}]
        }
    )
