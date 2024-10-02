import base64
import os
from typing import Dict, Any
from datetime import datetime
from typing import Annotated, List

import logging
import aiohttp
from core.config import settings
from fastapi import Body, Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI()


class AirflowService:
    def __init__(self):
        #self.base_url = settings.AIRFLOW_API_ENDPOINT
        #self.base_url = "http://localhost:8080/api/v1"
        self.base_url = 'http://airflow-webserver:8080/api/v1'
        self.auth_username = "airflow"
        self.auth_password = "airflow"
        self.auth_header = self._get_auth_header()

    def _get_auth_header(self):
        credentials = f"{self.auth_username}:{self.auth_password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded_credentials}"}

    async def trigger_dag(self, dag_id: str, dag_run_data: Dict[str, Any]) -> dict:
        async with aiohttp.ClientSession(headers=self.auth_header) as session:
            async with session.post(f"{self.base_url}/dags/{dag_id}/dagRuns", json=dag_run_data) as response:
                if response.status not in (200, 201):
                    error = await response.text()
                    logging.error(f"Erro ao acionar a DAG. Status: {response.status}, Resposta: {error}")
                    raise Exception(f"Falha ao acionar a DAG. Status: {response.status}, Resposta: {error}")
                return await response.json()
        
    async def get_dag_run(self, dag_id: str, dag_run_id: str) -> dict:
        async with aiohttp.ClientSession(headers=self.auth_header) as session:
            async with session.get(f"{self.base_url}/dags/{dag_id}/dagRuns/{dag_run_id}") as response:
                response.raise_for_status()
                return await response.json()


def get_airflow_service():
    return AirflowService()
