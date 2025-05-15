import logging
from typing import Union

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from .github_fetcher import GithubFetcher
from .routers import starneighbours
from .settings import Settings

settings = Settings()
app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
app.include_router(starneighbours.router)

github_fetcher = GithubFetcher(settings.github_key, log_level=logging.DEBUG)


"""debug page """


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.get("/info")
async def info():
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "admin_email": settings.admin_email,
        "github_account": settings.github_account,
    }


@app.get("/hello")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.get("/github/")
async def github_proxy(path: str):
    data, metadata = await github_fetcher.get(path)  # ! no sanity here !
    return {
        "data": data,
        "metadata": {
            "status": metadata.get("status", 200),  # Default to 200 for cache hits
            "ratelimit": {
                "remaining": metadata["headers"].get("X-RateLimit-Remaining"),
                "reset": metadata["headers"].get("X-RateLimit-Reset"),
            },
            "cached": metadata.get("cached", False),
            "headers": metadata.get("headers", {}),
        },
    }
