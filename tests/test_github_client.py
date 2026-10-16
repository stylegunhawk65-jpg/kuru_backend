"""Tests for GitHub API client rate-limiting, retries, and error handling."""

from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.services.github_client import (
    GitHubAPIError,
    GitHubClient,
    GitHubRateLimitError,
)


@pytest.mark.asyncio
async def test_github_rate_limit_detection():
    """Ensure HTTP 403 with x-ratelimit-remaining=0 raises GitHubRateLimitError."""
    client = GitHubClient(token="ghp_test_rate_limited")

    mock_response = httpx.Response(
        status_code=403,
        headers={
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": "1700000000",
        },
        content=b'{"message": "API rate limit exceeded"}',
        request=httpx.Request("GET", "https://api.github.com/user"),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        with pytest.raises(GitHubRateLimitError) as exc_info:
            await client.get_current_user()

        assert exc_info.value.status_code == 429
        assert "rate limit exceeded" in str(exc_info.value.detail).lower()
        assert exc_info.value.reset_timestamp == 1700000000


@pytest.mark.asyncio
async def test_github_invalid_token_error():
    """Ensure HTTP 401 returns 401 GitHubAPIError."""
    client = GitHubClient(token="ghp_bad_token")

    mock_response = httpx.Response(
        status_code=401,
        content=b'{"message": "Bad credentials"}',
        request=httpx.Request("GET", "https://api.github.com/user"),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        with pytest.raises(GitHubAPIError) as exc_info:
            await client.get_current_user()

        assert exc_info.value.status_code == 401
        assert "invalid or expired" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_github_skip_oversized_files():
    """Ensure get_file_content skips files exceeding MAX_ANALYSIS_FILE_SIZE_BYTES."""
    client = GitHubClient(token="ghp_test_token")

    # Mock file response with size 600 KB (> 500 KB threshold)
    mock_response = httpx.Response(
        status_code=200,
        json={"size": 600 * 1024, "content": "dGVzdA=="},
        request=httpx.Request("GET", "https://api.github.com/repos/o/r/contents/big.py"),
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        content = await client.get_file_content("owner", "repo", "big.py")
        assert content is None


@pytest.mark.asyncio
async def test_github_timeout_retry_and_failure():
    """Ensure network timeouts are handled and raise 504 GitHubAPIError."""
    client = GitHubClient(token="ghp_test_token", timeout=1.0)

    with patch(
        "httpx.AsyncClient.request",
        side_effect=httpx.TimeoutException("Connection timed out"),
    ):
        with pytest.raises(GitHubAPIError) as exc_info:
            await client.list_repositories()

        assert exc_info.value.status_code == 504
        assert "timed out" in str(exc_info.value.detail).lower()
