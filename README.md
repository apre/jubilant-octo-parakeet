# stargazer demo project

## known limitation

- no paging against github API, could have been way better
  - it must be implemented to cover repositories with 30+ stars or 30+ stargazers
- GithubFetcher test coverage could be largely improved

## thing I wish I could add
- a [viz.js](https://visjs.github.io/vis-network/examples/network/basicUsage.html) based visualization of the repositories
- a persistant disk cache for github calls that survive across app restart
- project configuration could be read from environment variables
- Dockerfile for easier deployment
- authentication based on JWT
- more unit test for the rate limiter



# bootstrap project

## create environment

```shell
conda env create -f environment.yaml
conda activate stargazer
cp template.env dev.env
# edit dev.env, insert your github api key in there.
```

## run project
```shell
fastapi dev app/main.py
```

# test it

[Bruno](https://www.usebruno.com/) can be used to test the api.
- You will need to feed the `GITHUB_TOKEN` in the `dev` environment.
- Bruno config files are in `tests/bruno` directory.
