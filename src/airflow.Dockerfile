FROM apache/airflow:2.10.1
COPY airflow.requirements.txt /
RUN pip install --no-cache-dir "apache-airflow==2.10.1" -r /airflow.requirements.txt