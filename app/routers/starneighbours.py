# https://fastapi.tiangolo.com/tutorial/bigger-applications/#apirouter


from fastapi import APIRouter

router = APIRouter()


@router.get("/repos/{user}/{repo}/starneighbours", tags=["gazer"])
async def get_starneighbours(user: str, repo: str):
    return []
