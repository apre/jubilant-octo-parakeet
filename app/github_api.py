

from .github_fetcher import GithubFetcher

"""high level github access methods.

uses the githubfetcher to fetch the data
allow to be mocked and cached

"""
class GithubAPI:
    def __init__(self, fetcher: GithubFetcher):
        self.fetcher = fetcher

    """returns list of stargazer of a given github repository.

    Todo: exception in case of error.
    """
    def get_repo_stargazers(self,user:str, repo: str):
        response, metadata = self.fetcher.get(f"https://api.github.com/repos/{user}/{repo}/stargazers",
                                              [("X-GitHub-Api-Version", "2022-11-28")])
        return [user.login for user in response]


    def get_starred_repo_of_user(self,user:str):
        return []
