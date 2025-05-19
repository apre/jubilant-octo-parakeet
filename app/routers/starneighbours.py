# https://fastapi.tiangolo.com/tutorial/bigger-applications/#apirouter

from fastapi import APIRouter

from ..github_api import get_github_api
from ..starneighbours_finder import starneighbours_finder

router = APIRouter()

@router.get("/repos/{user}/{repo}/starneighbours", tags=["gazer"])
async def get_starneighbours(user: str, repo: str):
    github_api = get_github_api()
    return await starneighbours_finder(github_api,user,repo)
