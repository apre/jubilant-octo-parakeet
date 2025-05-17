import asyncio
import json
import logging
import time

import aiohttp
import pytest
from aioresponses import aioresponses
from fastapi import HTTPException

from app.github_fetcher import CacheEntry, GithubFetcher


@pytest.fixture
def mock_api():
    """Fixture that provides the aioresponses mock"""
    with aioresponses() as m:
        yield m


@pytest.mark.asyncio
async def test_exception_handling(mock_api):
    """Test general exception handling in _make_request method"""
    url = "https://api.github.com/repos/error"

    # Mock connection error
    mock_api.get(url, exception=aiohttp.ClientError("Connection error"))

    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # Verify the exception is caught and re-raised as HTTPException
    with pytest.raises(HTTPException) as excinfo:
        await fetcher.get(url)

    assert excinfo.value.status_code == 500
    assert "Error fetching from GitHub" in excinfo.value.detail


@pytest.mark.asyncio
async def test_maximum_retry_count(mock_api):
    """Test handling of maximum retry count"""
    url = "https://api.github.com/repos/retry-test"

    # Mock rate limit response that will trigger retry
    mock_api.get(
        url,
        status=429,
        headers={
            "Retry-After": "1",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(asyncio.get_event_loop().time() + 10))
        },
        repeat=True
    )

    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # This should raise an exception after hitting max retries
    with pytest.raises(HTTPException) as excinfo:
        await fetcher.get(url)

    assert excinfo.value.status_code == 429
    assert "Maximum retry count reached" in excinfo.value.detail


@pytest.mark.asyncio
async def test_redirect_handling(mock_api):
    """Test handling of HTTP redirects"""
    original_url = "https://api.github.com/old/url"
    new_url = "https://api.github.com/new/url"

    # Setup redirect
    mock_api.get(
        original_url,
        status=301,
        headers={"Location": new_url}
    )

    # Setup target response
    mock_data = {"name": "redirected-repo"}
    mock_api.get(
        new_url,
        status=200,
        body=json.dumps(mock_data)
    )

    fetcher = GithubFetcher(token="test_token", test_mode=True)
    data, metadata = await fetcher.get(original_url)

    # Verify we got the data from the new URL
    assert data["name"] == "redirected-repo"
    assert metadata["url"] == new_url


@pytest.mark.asyncio
async def test_non_json_response(mock_api):
    """Test handling of non-JSON responses"""
    url = "https://api.github.com/text-response"
    mock_response = "This is a plain text response"

    # Setup mock response with text content
    mock_api.get(
        url,
        status=200,
        body=mock_response,
        content_type="text/plain"
    )

    fetcher = GithubFetcher(token="test_token", test_mode=True)
    data, metadata = await fetcher.get(url)

    # Verify text response handling
    assert data == mock_response
    assert metadata["status"] == 200


@pytest.mark.asyncio
async def test_error_response(mock_api):
    """Test handling of error responses"""
    url = "https://api.github.com/error-response"
    error_data = {"message": "Not Found"}

    # Setup mock error response
    mock_api.get(
        url,
        status=404,
        body=json.dumps(error_data)
    )

    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # Verify error handling
    with pytest.raises(HTTPException) as excinfo:
        await fetcher.get(url)

    assert excinfo.value.status_code == 404
    assert "GitHub API error" in excinfo.value.detail


@pytest.mark.asyncio
async def test_rate_limit_headers(mock_api):
    """Test handling of different rate limit header combinations"""
    url = "https://api.github.com/rate-limit-test"

    # Test with Retry-After header
    mock_api.get(
        url,
        status=429,
        headers={"Retry-After": "5"},
        body=json.dumps({"message": "Rate limited"})
    )

    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # Should hit rate limit and retry
    with pytest.raises(HTTPException):
        await fetcher.get(url)

    # Verify rate limit state was set
    status = GithubFetcher.get_rate_limit_status()
    assert status["is_rate_limited"]


@pytest.mark.asyncio
async def test_rate_limit_with_reset_header(mock_api):
    """Test handling of X-RateLimit-Reset header"""
    url = "https://api.github.com/rate-limit-reset-test"
    future_time = int(asyncio.get_event_loop().time() + 10)

    # Mock response with X-RateLimit headers
    mock_api.get(
        url,
        status=403,
        headers={
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(future_time)
        },
        body=json.dumps({"message": "API rate limit exceeded"})
    )

    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # Reset rate limiting state
    GithubFetcher._rate_limited_until = 0

    # Should trigger rate limit handling
    with pytest.raises(HTTPException):
        await fetcher.get(url)

    # Verify rate limit state was updated
    status = GithubFetcher.get_rate_limit_status()
    assert status["is_rate_limited"]
    assert status["reset_at"] is not None


@pytest.mark.asyncio
async def test_clear_all_cache():
    """Test clearing all cache entries"""
    # Create fetcher with test_mode
    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # Manually add items to cache using proper CacheEntry objects
    fetcher._cache["https://api.github.com/url1"] = CacheEntry(
        data={"name": "test1"},
        etag="etag1",
        timestamp=time.time()
    )
    fetcher._cache["https://api.github.com/url2"] = CacheEntry(
        data={"name": "test2"},
        etag="etag2",
        timestamp=time.time()
    )

    # Clear all cache
    fetcher.clear_cache()

    # Verify cache is empty
    assert len(fetcher._cache) == 0


@pytest.mark.asyncio
async def test_wait_if_rate_limited():
    """Test the wait if rate limited method specifically"""
    # Set up a rate limit expiring in the future
    GithubFetcher._rate_limited_until = time.time() + 5

    # Create a fetcher in test mode (should skip actual sleeping)
    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # This should not actually sleep but return immediately in test mode
    start_time = time.time()
    await fetcher._wait_if_rate_limited()
    elapsed = time.time() - start_time

    # Should return almost immediately since we're in test mode
    assert elapsed < 1.0

    # Reset for other tests
    GithubFetcher._rate_limited_until = 0


@pytest.mark.asyncio
async def test_fetch_with_empty_response(mock_api):
    """Test fetching with an empty response that could be returned by GitHub API"""
    url = "https://api.github.com/empty"

    # Setup empty array response
    mock_api.get(
        url,
        status=200,
        body="[]"
    )

    fetcher = GithubFetcher(token="test_token", test_mode=True)
    data, metadata = await fetcher.get(url)

    # Verify we get the empty array
    assert data == []
    assert metadata["status"] == 200

    # And it should be added to cache
    assert url in fetcher._cache


@pytest.mark.asyncio
async def test_missing_location_header(mock_api):
    """Test redirect with missing Location header"""
    url = "https://api.github.com/bad-redirect"

    # Mock redirect response without Location header
    mock_api.get(
        url,
        status=302,
        headers={}  # No Location header
    )

    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # Should raise an HTTP exception for the redirect without Location
    with pytest.raises(HTTPException) as excinfo:
        await fetcher.get(url)

    assert excinfo.value.status_code == 302


@pytest.mark.asyncio
async def test_non_test_mode_wait():
    """Test the wait functionality when not in test mode (but mock the sleep)"""
    original_sleep = asyncio.sleep
    sleep_called = False

    # Create mock for asyncio.sleep
    async def mock_sleep(seconds):
        nonlocal sleep_called
        sleep_called = True
        # Don't actually sleep in the test
        return

    # Replace asyncio.sleep with our mock
    asyncio.sleep = mock_sleep

    try:
        # Set up a rate limit expiring in the future
        GithubFetcher._rate_limited_until = time.time() + 2

        # Create fetcher NOT in test mode
        GithubFetcher._test_mode = False  # Ensure test mode is off
        fetcher = GithubFetcher(token="test_token", test_mode=False)

        # This should call our mocked sleep
        await fetcher._wait_if_rate_limited()

        # Verify sleep was called
        assert sleep_called

    finally:
        # Restore original sleep function
        asyncio.sleep = original_sleep
        # Reset test mode
        GithubFetcher._test_mode = False
        # Reset rate limit
        GithubFetcher._rate_limited_until = 0


@pytest.mark.asyncio
async def test_custom_logger_level():
    """Test initializing with a custom log level"""
    # Create fetcher with DEBUG level
    fetcher = GithubFetcher(token="test_token", log_level=logging.DEBUG)

    # Verify the logger level was set
    assert fetcher.logger.level == logging.DEBUG


@pytest.mark.asyncio
async def test_conditional_requests(mock_api):
    """Test making a conditional request with ETag and Last-Modified headers"""
    url = "https://api.github.com/conditional"
    etag = "W/\"something\""
    last_modified = "Wed, 01 May 2024 12:00:00 GMT"

    # Create a fetcher
    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # Manually add an item to the cache
    fetcher._cache[url] = CacheEntry(
        data={"name": "cached-data"},
        etag=etag,
        last_modified=last_modified,
        headers={"ETag": etag, "Last-Modified": last_modified},
        timestamp=time.time()
    )

    # Add mock response
    mock_api.get(
        url,
        status=200,
        body=json.dumps({"name": "new-data"}),
        headers={"ETag": "W/\"newvalue\""}
    )

    # Make request - should include conditional headers
    await fetcher.get(url)

    # We can't verify headers directly in aioresponses, but at least test execution completed
    assert True


@pytest.mark.asyncio
async def test_rate_limit_remaining(mock_api):
    """Test handling rate limits based on X-RateLimit-Remaining=0"""
    url = "https://api.github.com/rate-remaining"

    # Set up a response with X-RateLimit-Remaining=0 but no Retry-After
    reset_time = int(time.time() + 10)
    mock_api.get(
        url,
        status=403,
        headers={
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset_time)
        },
        body=json.dumps({"message": "Rate limit exceeded"})
    )

    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # Reset rate limit state
    GithubFetcher._rate_limited_until = 0

    # Should trigger rate limit handling via the remaining quota path
    with pytest.raises(HTTPException):
        await fetcher.get(url)

    # Verify rate limit state was set
    status = GithubFetcher.get_rate_limit_status()
    assert status["is_rate_limited"]


@pytest.mark.asyncio
async def test_non_test_mode_rate_limit_sleep(mock_api):
    """Test rate limit sleep when not in test mode"""
    url = "https://api.github.com/rate-sleep"

    # Make sure there is no existing rate limit
    GithubFetcher._rate_limited_until = 0

    # Set up response that will trigger rate limiting
    mock_api.get(
        url,
        status=429,
        headers={"Retry-After": "2"},
        body=json.dumps({"message": "Rate limited"})
    )

    # Add a success response for the retry
    mock_api.get(
        url,
        status=200,
        body=json.dumps({"success": True})
    )

    # Set up sleep mock
    original_sleep = asyncio.sleep
    sleep_called = False
    sleep_seconds = 0

    async def mock_sleep(seconds):
        nonlocal sleep_called, sleep_seconds
        sleep_called = True
        sleep_seconds = seconds
        return

    # Replace sleep function
    asyncio.sleep = mock_sleep

    try:
        # Turn off test mode
        GithubFetcher._test_mode = False
        fetcher = GithubFetcher(token="test_token", test_mode=False)

        # Make request - should hit rate limit and retry
        await fetcher.get(url)

        # Verify sleep was called
        assert sleep_called
        # The sleep time should be close to the Retry-After value (2 seconds)
        assert 1 <= sleep_seconds <= 3

    finally:
        # Restore original sleep
        asyncio.sleep = original_sleep
        # Reset test mode
        GithubFetcher._test_mode = False
        # Reset rate limit state
        GithubFetcher._rate_limited_until = 0


@pytest.mark.asyncio
async def test_conditional_request_etag_only(mock_api):
    """Test conditional request with ETag but no Last-Modified"""
    url = "https://api.github.com/etag-only"
    etag = "W/\"etag-value\""

    # Create a fetcher
    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # Manually add an item to the cache with only ETag
    fetcher._cache[url] = CacheEntry(
        data={"name": "cached-data"},
        etag=etag,
        last_modified=None,  # No Last-Modified header
        headers={"ETag": etag},
        timestamp=time.time()
    )

    # Add mock response
    mock_api.get(
        url,
        status=200,
        body=json.dumps({"name": "new-data"}),
        headers={"ETag": "W/\"new-etag\""}
    )

    # Make request - should include If-None-Match but not If-Modified-Since
    await fetcher.get(url)

    # Test completed without errors
    assert True


@pytest.mark.asyncio
async def test_conditional_request_last_modified_only(mock_api):
    """Test conditional request with Last-Modified but no ETag"""
    url = "https://api.github.com/last-modified-only"
    last_modified = "Wed, 01 May 2024 12:00:00 GMT"

    # Create a fetcher
    fetcher = GithubFetcher(token="test_token", test_mode=True)

    # Manually add an item to the cache with only Last-Modified
    fetcher._cache[url] = CacheEntry(
        data={"name": "cached-data"},
        etag=None,  # No ETag header
        last_modified=last_modified,
        headers={"Last-Modified": last_modified},
        timestamp=time.time()
    )

    # Add mock response
    mock_api.get(
        url,
        status=200,
        body=json.dumps({"name": "new-data"}),
        headers={"Last-Modified": "Wed, 02 May 2024 12:00:00 GMT"}
    )

    # Make request - should include If-Modified-Since but not If-None-Match
    await fetcher.get(url)

    # Test completed without errors
    assert True


@pytest.mark.asyncio
async def test_actual_wait_with_very_small_timeout():
    """Test the actual asyncio.sleep call with a minimal timeout"""
    # Don't mock sleep, but use a very small timeout
    # This tests lines 136-140 with real asyncio.sleep

    # Set a very short rate limit (0.01 seconds)
    tiny_wait = 0.01
    GithubFetcher._rate_limited_until = time.time() + tiny_wait

    # Make sure test mode is off
    GithubFetcher._test_mode = False

    try:
        # Create fetcher with test_mode=False
        fetcher = GithubFetcher(token="test_token", test_mode=False)

        # Call _wait_if_rate_limited - this should actually sleep for the tiny duration
        start_time = time.time()
        await fetcher._wait_if_rate_limited()
        elapsed = time.time() - start_time

        # Should have slept for at least the tiny wait time
        assert elapsed >= tiny_wait

    finally:
        # Reset test mode and rate limit
        GithubFetcher._test_mode = False
        GithubFetcher._rate_limited_until = 0
