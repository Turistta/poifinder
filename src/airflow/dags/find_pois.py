import os
import sys

# Adicionar o diretório de dags ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import logging
from typing import Any, Dict, List

import pendulum
from airflow.decorators import dag, task
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from common.find_pois_functions import (
    load_data,
    request_pois,
    parse_pois,
    apply_filtering,
    process_filtered_pois,
    return_results,
    check_sync_trigger,
)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": pendulum.yesterday(),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": pendulum.duration(minutes=3),
}

@dag(
    dag_id="find_pois",
    default_args=default_args,
    description="DAG para filtrar POIs com base nas preferências do usuário e localização.",
    schedule_interval=None,
    catchup=False,
)

def find_pois():
    @task
    def load_data_task(**kwargs):
        return load_data(**kwargs)

    @task
    def request_pois_task(conf):
        return request_pois(conf)

    @task
    def parse_pois_task(pois_gdf):
        return parse_pois(pois_gdf)

    @task
    def apply_filtering_task(parsed_pois, conf):
        return apply_filtering(parsed_pois, conf)

    @task
    def process_filtered_pois_task(filtered_pois, conf):
        return process_filtered_pois(filtered_pois, conf)

    @task
    def return_results_task(results):
        return return_results(results)

    @task
    def check_sync_trigger_task():
        return check_sync_trigger()

    sync_trigger = TriggerDagRunOperator(
        task_id="sync_trigger",
        trigger_dag_id="sync_pois",
    )

    user_data = load_data_task()
    raw_response = request_pois_task(user_data)
    parsed_pois = parse_pois_task(raw_response)
    filtered_pois = apply_filtering_task(parsed_pois, user_data)
    processed_pois = process_filtered_pois_task(filtered_pois, user_data)
    return_results_task(processed_pois) >> check_sync_trigger_task() >> sync_trigger

find_pois_dag = find_pois()
