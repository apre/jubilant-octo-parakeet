from collections import Counter
from typing import List

import pytest

from app.github_api import GithubAPI
from app.starneighbours_finder import starneighbours_finder


# mock github api for reproductible algorithm desing and tests
class GithubAPIMock(GithubAPI):
    def __init__(self):
        super().__init__(fetcher=None)
        self.stars = {}
        self.stars["u1"] = ["a","b", "d"]
        self.stars["u2"] = ["a","b", "c"]
        self.stars["u3"] = ["a","c", "e"]
        self.stars["u4"] = ["a","e"]

    async def get_repo_stargazers(self,user:str, repo: str):
        return ["u1","u2","u3","u4"]

    async def get_starred_repo_of_user(self,user:str):
        return self.stars[user]



def pick_repo_in_list(name:str, repo_list: List[dict]):
    """pick a repo map whos "repo" attributes watches the wanted name. used as helper in asserts"""
    for repo in repo_list:
        if repo["repo"] == name:
            return repo
    return None

def test_pick_repo_in_list():
    list_of_neighbours = [{'repo': 'b', 'stargazers': ['u1', 'u2']}, {'repo': 'c', 'stargazers': ['u2', 'u3']}, {'repo': 'e', 'stargazers': ['u3', 'u4']}]

    assert pick_repo_in_list("not_here",list_of_neighbours) is None

    neighbours =  pick_repo_in_list("b",list_of_neighbours)
    assert neighbours is not None
    assert len(neighbours['stargazers']) == 2
    assert "u1" in neighbours['stargazers']
    assert "u2" in neighbours['stargazers']


"""
     u1 gave stars to a,b,  d
     u2 gave stars to a,b,c
     u3 gave stars to a,  c,   e
     u4 gave stars to a,       e

     All users have repo A in common


"""
@pytest.mark.asyncio
async def test_starneighbours_finder():

    api = GithubAPIMock()
    neighbours = await starneighbours_finder(api,"u1", "a")

    a = pick_repo_in_list("a", neighbours)
    assert Counter(a['stargazers']) == Counter(['u1', 'u2', 'u3', 'u4'])

    b = pick_repo_in_list("b", neighbours)
    assert Counter(b['stargazers']) == Counter(['u1', 'u2'])

    c = pick_repo_in_list("c", neighbours)
    assert Counter(c['stargazers']) == Counter(['u2', 'u3'])

    e = pick_repo_in_list("e", neighbours)
    assert Counter(e['stargazers']) == Counter(['u3', 'u4'])
