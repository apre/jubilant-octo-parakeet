

# usefull apis:

## list stargazers of a repo  0,

doc here: https://docs.github.com/en/rest/activity/starring?apiVersion=2022-11-28#list-stargazers
GET   https://api.github.com/repos/OWNER/REPO/stargazers

curl -L \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer <YOUR-TOKEN>" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/OWNER/REPO/stargazers


## list repository stared by a user

doc here: https://docs.github.com/en/rest/activity/starring?apiVersion=2022-11-28#list-repositories-starred-by-a-user






# notes on github api

from https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api?apiVersion=2022-11-28#use-conditional-requests-if-appropriate


# TL;DR

- avoid concurrent requests
- look at `x-ratelimit-*` headers for ratelimitation informations
- error 403 / 420 : look at `retry-after` header and `x-ratelimit-remaining`
- use conditional requests (`etag` + `last-modified` header)

# Avoid concurrent requests

To avoid exceeding secondary rate limits, you should make requests serially instead of concurrently. To achieve this, you can implement a queue system for requests.

# Pause between mutative requests

If you are making a large number of POST, PATCH, PUT, or DELETE requests, wait at least one second between each request. This will help you avoid secondary rate limits.


# Handle rate limit errors appropriately

If you receive a rate limit error, you should stop making requests temporarily according to these guidelines:

* If the retry-after response header is present, you should not retry your request until after that many seconds has elapsed.
* If the x-ratelimit-remaining header is 0, you should not make another request until after the time specified by the x-ratelimit-reset header. The x-ratelimit-reset header is in UTC epoch seconds.
* Otherwise, wait for at least one minute before retrying. If your request continues to fail due to a secondary rate limit, wait for an exponentially increasing amount of time between retries, and throw an error after a specific number of retries.

Continuing to make requests while you are rate limited may result in the banning of your integration.

# Handle rate limit errors appropriately

If you receive a rate limit error, you should stop making requests temporarily according to these guidelines:

    If the retry-after response header is present, you should not retry your request until after that many seconds has elapsed.
    If the x-ratelimit-remaining header is 0, you should not make another request until after the time specified by the x-ratelimit-reset header. The x-ratelimit-reset header is in UTC epoch seconds.
    Otherwise, wait for at least one minute before retrying. If your request continues to fail due to a secondary rate limit, wait for an exponentially increasing amount of time between retries, and throw an error after a specific number of retries.

Continuing to make requests while you are rate limited may result in the banning of your integration.
