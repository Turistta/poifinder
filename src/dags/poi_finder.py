from airflow.decorators import dag, task

from models.models import AirflowDAGConf


@dag(dag_id="poi_finder")
def find_poi(conf: AirflowDAGConf):
    pass
