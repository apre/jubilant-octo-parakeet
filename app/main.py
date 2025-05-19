import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers import rotten, starneighbours
from .settings import settings

logger = logging.getLogger(__name__)
logger.setLevel(settings.log_level)

logger.info(f"environment: {settings.environment}")

app = FastAPI(
    title='stargazer application',
    version='0.9.0',
)

app.include_router(starneighbours.router)
if settings.environment == "dev":
    # in case of dev environment, add some more routes (to help testing)
    app.include_router(rotten.router)
    app.mount("/static", StaticFiles(directory="static", html=True), name="static")
    logger.info("including rotten stufs")
