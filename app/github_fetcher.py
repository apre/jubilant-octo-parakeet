"""GithubFetcher: frontend to github apis, trying to respect API endpoint limitations.
- honor the caching
- tries to honor timing, should work in mono-processes
- preliminary paging support

Some code in this file have been written using AI


"""
import asyncio
import logging
import time
from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, NamedTuple, Optional, Tuple, Union

import aiohttp
from fastapi import HTTPException

from app.utils import setup_logger


class CacheEntry(NamedTuple):
    """Data structure for cache entries"""

    data: Any
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    timestamp: float = 0


class GithubFetcher:
    _rate_limited_until = 0  # Timestamp when rate limit expires
    _rate_limit_lock = None  # Class-level lock for rate limit state
    _test_mode = False  # When True, skips actual sleeping for tests

    def __init__(
        self, token: Optional[str] = None, concurrency: int = 1, log_level: int = logging.INFO, test_mode: bool = False
    ):
        """
        Initialize the GitHub Fetcher.

        Args:
            token: GitHub API token for authentication
            concurrency: Maximum number of concurrent requests allowed (default: 1)
            log_level: Logging level (default: logging.INFO)
            test_mode: When True, skips actual sleeping for faster tests
        """
        self.token = token
        self._semaphore = asyncio.Semaphore(concurrency)  # Allow configurable concurrency
        self._cache = {}  # Single cache dictionary to store all cache entries

        # Set test mode
        if test_mode:
            GithubFetcher._test_mode = True

        # Initialize class-level lock if not already initialized
        if GithubFetcher._rate_limit_lock is None:
            GithubFetcher._rate_limit_lock = asyncio.Lock()

        # todo: move logger init outside this class and pass it as parameter
        self.logger = setup_logger("github_fetcher", log_level)
        self.logger.info("GithubFetcher initialized")

    async def get(self, url: str, additionals_headers=[]) -> Tuple[Union[Dict[str, Any], str], Dict[str, Any]]:
        """
        Make a GET request to the GitHub API, trying to follow best practices.

        Args:
            url: The API endpoint path (will be appended to base_url if not a full URL)

        Returns:
            Tuple containing (response_data, metadata)
            - response_data: The JSON data or text from the response
            - metadata: Dict with status, headers, etc.
        """

        # Check cache first
        if url in self._cache:
            self.logger.debug(f"Cache hit for {url}")
            cache_entry = self._cache[url]
            return cache_entry.data, {"headers": cache_entry.headers or {}, "cached": True}

        # Check if we're in a global rate-limited state
        await self._wait_if_rate_limited()

        self.logger.debug(f"Making request to {url}")

        # Prepare headers
        headers = {"Accept": "application/vnd.github+json"}
        for (name, value)  in additionals_headers:
            headers[name] = value

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Add conditional request headers if available from cache
        if url in self._cache:
            cache_entry = self._cache[url]
            if cache_entry.etag:
                headers["If-None-Match"] = cache_entry.etag
            if cache_entry.last_modified:
                headers["If-Modified-Since"] = cache_entry.last_modified

        # Use semaphore to ensure limited concurrent requests
        async with self._semaphore:
            return await self._make_request(url, headers)

    async def _wait_if_rate_limited(self):
        """Wait if there's a global rate limit in effect"""
        current_time = time.time()

        if GithubFetcher._rate_limited_until > current_time:
            wait_time = GithubFetcher._rate_limited_until - current_time
            self.logger.warning(
                f"Global rate limit in effect. Waiting {wait_time:.1f}s before making request."
            )

            # Skip actual sleeping in test mode
            if GithubFetcher._test_mode:
                self.logger.debug("Test mode: skipping actual sleep")
                return

            await asyncio.sleep(wait_time)

    async def _make_request(
        self, url: str, headers: Dict[str, str], retry_count: int = 0
    ) -> Tuple[Union[Dict[str, Any], str], Dict[str, Any]]:
        """Internal method to make the actual request with retry logic"""
        # Prevent infinite recursion
        if retry_count >= 2:  # Max 2 retries
            self.logger.warning(f"Maximum retry count reached for {url}")
            raise HTTPException(
                status_code=HTTPStatus.TOO_MANY_REQUESTS,
                detail="Maximum retry count reached"
            )

        try:
            async with aiohttp.ClientSession() as session:
                self.logger.debug(f"Sending request to {url}")
                async with session.get(url, headers=headers, allow_redirects=True) as response:
                    self.logger.debug(f"Received response from {url}: status={response.status}")

                    # Handle 304 Not Modified (conditional request hit)
                    if response.status == HTTPStatus.NOT_MODIFIED and url in self._cache:
                        self.logger.info(f"304 Not Modified for {url}, using cached response")
                        cache_entry = self._cache[url]
                        # Update cache timestamp
                        self._cache[url] = cache_entry._replace(timestamp=time.time())
                        return cache_entry.data, {
                            "headers": cache_entry.headers or {},
                            "cached": True,
                        }

                    # Prepare response headers
                    response_headers = dict(response.headers)

                    # Prepare response data
                    try:
                        data = await response.json()
                        self.logger.debug(f"Parsed JSON response from {url}")
                    except aiohttp.ContentTypeError:
                        data = await response.text()
                        self.logger.debug(f"Parsed text response from {url}")

                    # Create metadata
                    metadata = {
                        "status": response.status,
                        "headers": response_headers,
                        "url": str(response.url),
                        "cached": False,
                    }

                    # Handle rate limiting
                    if response.status in (HTTPStatus.FORBIDDEN, HTTPStatus.TOO_MANY_REQUESTS):
                        self.logger.warning(f"Rate limit hit for {url}: status={response.status}")
                        retry_after = await self._handle_rate_limit(response_headers)
                        if retry_after > 0:
                            self.logger.info(f"Waiting {retry_after} seconds before retrying")

                            # Skip actual sleeping in test mode
                            if GithubFetcher._test_mode:
                                self.logger.debug("Test mode: skipping actual sleep")
                            else:
                                await asyncio.sleep(retry_after)

                            return await self._make_request(url, headers, retry_count + 1)

                    # Handle redirects (should be automatic with aiohttp, but just in case)
                    if response.status in (HTTPStatus.MOVED_PERMANENTLY, HTTPStatus.FOUND, HTTPStatus.TEMPORARY_REDIRECT):
                        new_url = response_headers.get("Location")
                        # print new location in logs
                        self.logger.info(f"Redirecting {url} to {new_url}")
                        if new_url:
                            return await self._make_request(new_url, headers, retry_count + 1)

                    # Cache the successful response
                    if 200 <= response.status < 300:
                        self.logger.debug(f"Caching successful response for {url}")
                        etag = response_headers.get("ETag")
                        last_modified = response_headers.get("Last-Modified")

                        self._cache[url] = CacheEntry(
                            data=data,
                            etag=etag,
                            last_modified=last_modified,
                            headers=response_headers,
                            timestamp=time.time(),
                        )

                    else: # Handle errors
                        self.logger.error(f"Error response from {url}: status={response.status}")
                        raise HTTPException(
                            status_code=response.status, detail=f"GitHub API error: {data}"
                        )

                    return data, metadata
        except Exception as e:
            self.logger.error(f"Exception during request to {url}: {str(e)}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=f"Error fetching from GitHub: {str(e)}")

    async def _handle_rate_limit(self, headers: Dict[str, str]) -> float:
        """
        Handle rate limit headers and return seconds to wait before retrying.
        Also updates the global rate limit state.
        """
        wait_time = 60.0  # Default wait time (1 minute)

        # Check retry-after header first (highest priority)
        if "Retry-After" in headers:
            wait_time = float(headers["Retry-After"])
            self.logger.info(f"Retry-After header found: {wait_time}s")
        # Check if we're out of rate limit quota
        elif int(headers.get("X-RateLimit-Remaining", "1")) == 0:
            reset_time = int(headers.get("X-RateLimit-Reset", "0"))
            if reset_time > 0:
                current_time = time.time()
                wait_time = max(1, reset_time - current_time)
                self.logger.info(
                    f"Rate limit exhausted. Reset at {datetime.fromtimestamp(reset_time).strftime('%H:%M:%S')} (in {wait_time:.1f}s)"
                )

        # Update global rate limit state with lock to avoid race conditions
        async with GithubFetcher._rate_limit_lock:
            new_rate_limit_end = time.time() + wait_time
            # Only update if the new time is later than the current one
            if new_rate_limit_end > GithubFetcher._rate_limited_until:
                GithubFetcher._rate_limited_until = new_rate_limit_end
                self.logger.warning(
                    f"Rate limit encountered. All workers paused until {datetime.fromtimestamp(new_rate_limit_end).strftime('%H:%M:%S')}."
                )

        return wait_time

    def clear_cache(self, url: Optional[str] = None):
        """
        Clear the cache for a specific URL or all URLs.

        Args:
            url: URL to clear from cache, or None to clear all cache
        """
        if url is not None:
            if url in self._cache:
                del self._cache[url]
                self.logger.debug(f"Cleared cache for {url}")
        else:
            self._cache.clear()
            self.logger.debug("Cleared all cache entries")

    @classmethod
    def get_rate_limit_status(cls) -> Dict[str, Any]:
        """
        Get current rate limit status.

        Returns:
            Dictionary with rate limit information
        """
        current_time = time.time()
        is_limited = cls._rate_limited_until > current_time
        seconds_remaining = max(0, cls._rate_limited_until - current_time) if is_limited else 0

        return {
            "is_rate_limited": is_limited,
            "seconds_remaining": seconds_remaining,
            "reset_at": datetime.fromtimestamp(cls._rate_limited_until).strftime("%H:%M:%S") if is_limited else None,
        }
