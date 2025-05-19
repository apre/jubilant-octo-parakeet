"""Development and testing routes.

This module contains routes that are only intended for development and testing purposes.
These routes should not be deployed in production.
"""
from fastapi import APIRouter
from starlette.responses import FileResponse

from ..github_api import get_github_api
from ..settings import PROJECT_ROOT, STATIC_DIR, settings

router = APIRouter(tags=["debug"])

@router.get("/README.md")
async def get_readme():
    """Serve the debug page from static files."""
    return FileResponse(PROJECT_ROOT / "README.md")

@router.get("/")
async def get_index():
    """Serve the debug page from static files."""
    return FileResponse(STATIC_DIR / "index.html")

@router.get("/info")
async def info():
    """Return application configuration information."""
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "admin_email": settings.admin_email,
    }

# Test routes for GitHub API integration
@router.get("/repos/{user}/{repo}/stargazers", tags=["gazer"])
async def get_repo_stargazers(user: str, repo: str):
    """Get stargazers for a specific repository.

    Args:
        user: GitHub username
        repo: Repository name
    """
    github_api = get_github_api()
    return await github_api.get_repo_stargazers(user, repo)

@router.get("/{user}/starred", tags=["gazer"])
async def get_user_stars(user: str):
    """Get repositories starred by a specific user.

    Args:
        user: GitHub username
    """
    github_api = get_github_api()
    return await github_api.get_starred_repo_of_user(user)
