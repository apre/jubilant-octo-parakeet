

import logging
from functools import lru_cache

from .github_fetcher import GithubFetcher
from .settings import settings

"""high level github access methods.

uses the GithubFetcher for low-lovel api access.
allow to be mocked and cached

possible improvements:
- add more aggressive caching (on disk/db)

"""
class GithubAPI:
    def __init__(self, fetcher: GithubFetcher):
        self.fetcher = fetcher

    """returns list of stargazer of a given github repository.

    Todo: exception in case of error.
    """
    async def get_repo_stargazers(self,user:str, repo: str):
        response, metadata = await self.fetcher.get(f"https://api.github.com/repos/{user}/{repo}/stargazers",
                                              [("X-GitHub-Api-Version", "2022-11-28")])
        return [stargazer['login'] for stargazer in response]

    async def get_starred_repo_of_user(self,user:str):
        response, metadata = await self.fetcher.get(f"https://api.github.com/users/{user}/starred",
                                              [("X-GitHub-Api-Version", "2022-11-28")])
        return [repo['name'] for repo in response]


@lru_cache()
def get_github_api() -> GithubAPI:
    fetcher = GithubFetcher(settings.github_key, log_level=logging.DEBUG)
    return GithubAPI(fetcher)
