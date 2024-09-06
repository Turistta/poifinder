import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from routes import client, service

logger = logging.getLogger(__name__)

app = FastAPI(title="POIFinder")

app.include_router(client.router)
app.include_router(service.router)


@app.get("/", include_in_schema=False)
async def redirect_docs():
    return RedirectResponse(url="/docs")
