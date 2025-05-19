from .github_api import GithubAPI


async def starneighbours_finder(github_api: GithubAPI,  user:str, target_repo: str):

    stargazers = await github_api.get_repo_stargazers(user, target_repo)

    # map of repositories -> [user list]
    repositories = {}

    for user in stargazers:
        repos_of_user = await github_api.get_starred_repo_of_user(user)
        #print(f"repo of user {user} has {len(repos_of_user)} : {repos_of_user}")
        for repo in repos_of_user:
            repositories.setdefault(repo, []).append(user)
            #repositories[repo] = repositories.get(repo,[]).append(user)

    # we exclude the target_repo from the list, and keep neighbours with at least 2 stargazers
    result = [
        {"repo": repo, "stargazers": list(users)}
        for repo, users in repositories.items()
        #if (len(users) > 1 and repo is not target_repo)
    ]

    return result
