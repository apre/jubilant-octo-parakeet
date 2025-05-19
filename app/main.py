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
# Mount static files directory
# Mount project root to serve README.md
#app.mount("/", StaticFiles(directory=str(PROJECT_ROOT)), name="root")

app.include_router(starneighbours.router)
if settings.environment == "dev":
    app.include_router(rotten.router)
    app.mount("/static", StaticFiles(directory="static", html=True), name="static")
    logger.info("including rotten stufs")
