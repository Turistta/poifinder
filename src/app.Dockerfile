FROM python:3.12.5

WORKDIR /api

COPY ./app.requirements.txt ./app.requirements.txt


RUN pip install --no-cache-dir --upgrade -r app.requirements.txt

COPY ./common ./common
COPY ./app ./app
WORKDIR ./app
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]