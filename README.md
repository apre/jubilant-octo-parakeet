# stargazer demo project

# boot strap project

First time

```shell
conda create -n stargazer python=3.11 fastapi pytest pydantic pydantic-settings aiohttp fastcore pytest-asyncio aioresponses pytest-cov
conda activate stargazer

# create requirement file
conda list --export > requirements.txt

```

# design.

- first approach based on simple get on https://api.github.com/repos/{user}/{repo}/stargazers
- but tenacity repo has 7k stargazers, requiring 233 requests for fetching them all.



# test it


[Bruno](https://www.usebruno.com/) can be used to test the api.
