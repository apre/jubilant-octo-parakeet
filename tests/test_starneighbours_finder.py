from collections import Counter
from typing import List

from app.github_api import GithubAPI
from app.starneighbours_finder import starneighbours_finder


class GithubAPIMock(GithubAPI):
    def __init__(self):
        super().__init__(fetcher=None)
        self.stars = {}
        self.stars["u1"] = ["a","b", "d"]
        self.stars["u2"] = ["a","b", "c"]
        self.stars["u3"] = ["a","c", "e"]
        self.stars["u4"] = ["a","e"]



    def get_repo_stargazers(self,user:str, repo: str):
        return ["u1","u2","u3","u4"]

    def get_starred_repo_of_user(self,user:str):
        return self.stars[user]





def pick_repo_in_list(name:str, repo_list: List[dict]):
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

def test_starneighbours_finder():
    api = GithubAPIMock()

    # u1 gave stars to a,b,  d
    # u2 gave stars to a,b,c
    # u3 gave stars to a,  c,   e
    # u4 gave stars to a,       e

    # so we have neighbours:
    # [a,b  ,d ] from  u1
    # [a,b,c   ] from  u2
    # [a,  c, e] from  u3
    # [a,     e] from  u3

    # d has only u1 -> not a starneighbour

    # neighboours with one stargazer in common
    # b has u1, u2
    # c has u2 and u4
    # e has u3 and u4

    #    api.get_repo_stargazers.return_value = ["u1","u2", "u3", "u4"]

    neighbours = starneighbours_finder(api,"u1", "a")
    print(neighbours  )
    assert len(neighbours) == 3
    assert all(entry["repo"] != "a" for entry in neighbours) #  check that a is NOT in list

    b = pick_repo_in_list("b", neighbours)
    assert Counter(b['stargazers']) == Counter(['u1', 'u2'])

    c = pick_repo_in_list("c", neighbours)
    assert Counter(c['stargazers']) == Counter(['u2', 'u3'])

    e = pick_repo_in_list("e", neighbours)
    assert Counter(e['stargazers']) == Counter(['u3', 'u4'])
