from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field

from .base_models import HexUUIDString


class AirflowJobStatus(BaseModel):
    """Response from the Airflow REST API. Information on the DAG run from an AirflowDagTriggerRequest."""

    job_id: Annotated[HexUUIDString, Field(description="Unique identifier for the Airflow job")]
    start_date: Annotated[Optional[str], Field(description="Start time of the DAG run")]
    end_date: Annotated[Optional[str], Field(description="End time of the DAG run")]
    state: Annotated[str, Field(description="States of DAG. Can be: 'QUEUED', 'RUNNING', 'SUCCESS', 'FAILED'")]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "550e8400e29b41d4a716446655440000",
                "start_date": "2024-06-15T10:00:00Z",
                "end_date": "2024-06-15T10:05:30Z",
                "state": "RUNNING",
            }
        }
    )


class SyncRequest(BaseModel):
    """Sync request for the FastAPI endpoint"""

    trigger: Annotated[bool, Field(description="Flag to trigger the sync operation (should be true)")]

    model_config = ConfigDict(json_schema_extra={"example": {"trigger": True}})


class SyncResponse(BaseModel):
    """Sync response from the FastAPI endpoint"""

    status: Annotated[
        str, Field(description="The status of the sync operation (e.g., success or failure)")
    ]  # TODO: Use enum
    message: Annotated[str, Field(description="Message providing additional information about the sync result")]
    timestamp: Annotated[str, Field(description="Timestamp of when the operation was completed, in ISO 8601 format")]
    operation_id: Annotated[str, Field(description="Unique identifier for tracking the sync operation")]

    model_config = ConfigDict(  # TODO: Placeholder
        json_schema_extra={
            "example": {
                "status": "SUCCESS",
                "message": "Sync completed successfully",
                "timestamp": "2024-09-06T12:34:56Z",
                "operation_id": "12345",
            }
        }
    )
