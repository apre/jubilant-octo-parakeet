import json
import time

import pytest
from aioresponses import aioresponses

from app.github_fetcher import GithubFetcher


@pytest.fixture
def mock_api():
    """Fixture that provides the aioresponses mock"""
    with aioresponses() as m:
        yield m

@pytest.mark.asyncio
async def test_get_success(mock_api):
    """Test successful API request with aioresponses"""
    # Mock data
    mock_data = {"company": "Aperture science", "id": 1, "ceo": "Cave Johnson"}
    mock_headers = {"ETag": "W/\"12345\"", "Last-Modified": "Wed, 04 Jul 1981 12:00:00 GMT"}

    # Setup mock response
    url = "https://api.fake.com/user"
    mock_api.get(url, status=200, body=json.dumps(mock_data), headers=mock_headers)

    # Create fetcher and make request
    fetcher = GithubFetcher(token="test_token", test_mode=True)
    data, metadata = await fetcher.get(url)

    # Verify results
    assert data["company"] == "Aperture science"
    assert data["ceo"] == "Cave Johnson"
    assert not metadata["cached"]
    assert metadata["headers"]["ETag"] == "W/\"12345\""

    # Verify the request was made - just ensure we have some request to this URL
    assert len(mock_api.requests) > 0


@pytest.mark.asyncio
async def test_cache_mechanism(mock_api):
    """Test the caching mechanism with conditional requests"""
    url = "https://api.fake.com/user"
    etag = "W/\"abcdef12345\""
    mock_data = {"company": "Aperture science", "id": 1, "ceo": "Cave Johnson"}

    # First request returns 200 with ETag
    mock_api.get(
        url,
        status=200,
        body=json.dumps(mock_data),
        headers={"ETag": etag}
    )

    # Second request with matching ETag returns 304
    mock_api.get(
        url,
        status=304,
        headers={"ETag": etag}
    )

    # Create fetcher and make first request
    fetcher = GithubFetcher(token="test_token", test_mode=True)
    data1, metadata1 = await fetcher.get(url)

    # Verify first response
    assert data1["company"] == "Aperture science"
    assert not metadata1["cached"]

    # Make second request, should use conditional request and get 304
    data2, metadata2 = await fetcher.get(url)

    # Verify second response uses cache
    assert metadata2["cached"]
    assert data1 == data2


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test the rate limiting status mechanism
    AI generated, not verified by human
    """
    # Reset rate limiting state
    GithubFetcher._rate_limited_until = 0

    # Initially, there should be no rate limiting
    initial_status = GithubFetcher.get_rate_limit_status()
    assert not initial_status["is_rate_limited"]

    # Manually set the rate limit to 5 seconds from now
    future_time = time.time() + 5
    GithubFetcher._rate_limited_until = future_time

    # Check that rate limiting is now active
    rate_limit_status = GithubFetcher.get_rate_limit_status()
    assert rate_limit_status["is_rate_limited"]
    assert 0 < rate_limit_status["seconds_remaining"] <= 5

    # Reset for other tests
    GithubFetcher._rate_limited_until = 0


@pytest.mark.asyncio
async def test_not_modified_response(mock_api):
    """Test handling 304 Not Modified responses
        AI generated, not verified by human

    """
    url = "https://api.fake.com/repos/octocat/hello-world"
    etag = "W/\"12345abcdef\""

    # Setup initial response with ETag
    mock_api.get(
        url,
        status=200,
        body=json.dumps({"name": "hello-world", "stars": 100}),
        headers={"ETag": etag, "Last-Modified": "Wed, 01 Jan 2023 12:00:00 GMT"}
    )

    # Setup 304 response for conditional request
    mock_api.get(
        url,
        status=304,
        headers={"ETag": etag}
    )

    # Create fetcher
    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # First request to populate cache
    data1, metadata1 = await fetcher.get(url)

    # Verify initial response
    assert data1["name"] == "hello-world"
    assert not metadata1["cached"]

    # Second request should be cached via 304
    data2, metadata2 = await fetcher.get(url)

    # Verify 304 response
    assert metadata2["cached"]
    assert data1 == data2


@pytest.mark.asyncio
async def test_manual_cache_clearing(mock_api):
    """Test manually clearing the cache
        AI generated, not verified by human

    """
    url = "https://api.fake.com/user"

    # Setup response
    mock_api.get(
        url,
        status=200,
        body=json.dumps({"login": "octocat"}),
        headers={"ETag": "W/\"12345\""}
    )

    # Create fetcher
    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # Make request to populate cache
    await fetcher.get(url)

    # Clear specific URL from cache
    fetcher.clear_cache(url)

    # Verify cache is empty for that URL
    assert url not in fetcher._cache

    # Make request again
    mock_api.get(
        url,
        status=200,
        body=json.dumps({"login": "octocat"}),
        headers={"ETag": "W/\"12345\""}
    )
    data, metadata = await fetcher.get(url)

    # Should not be from cache
    assert not metadata["cached"]
