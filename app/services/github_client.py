"""Asynchronous GitHub API client with rate-limiting, pagination, and error handling."""

import base64
from datetime import datetime, timezone
import logging
from typing import Any
import httpx

from app.core.exceptions import AppException

logger = logging.getLogger("kuru.github_client")

GITHUB_API_BASE = "https://api.github.com"
MAX_ANALYSIS_FILE_SIZE_BYTES = 500 * 1024  # 500 KB limit for static manifest analysis


class GitHubRateLimitError(AppException):
    """Raised when GitHub API rate limits are exhausted."""

    def __init__(self, reset_timestamp: int | None = None):
        reset_time_str = (
            datetime.fromtimestamp(reset_timestamp, timezone.utc).isoformat()
            if reset_timestamp
            else "soon"
        )
        super().__init__(
            detail=f"GitHub API rate limit exceeded. Reset expected at {reset_time_str}.",
            status_code=429,
            error_code="GITHUB_RATE_LIMIT_EXCEEDED",
        )
        self.reset_timestamp = reset_timestamp


class GitHubAPIError(AppException):
    """Raised on non-transient GitHub API errors."""

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(
            detail=detail,
            status_code=status_code,
            error_code="GITHUB_API_ERROR",
        )


class GitHubClient:
    """Async client interacting with the GitHub REST API using user token."""

    def __init__(self, token: str, timeout: float = 15.0):
        self.token = token.strip()
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Kuru-Career-Twin/1.0",
        }
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        retries: int = 2,
    ) -> httpx.Response:
        """Execute request with rate limit inspection and transient error retries."""
        url = f"{GITHUB_API_BASE}{path}" if path.startswith("/") else path

        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        params=params,
                    )

                # Check rate limit headers
                remaining = response.headers.get("x-ratelimit-remaining")
                if response.status_code in (403, 429) and remaining == "0":
                    reset_header = response.headers.get("x-ratelimit-reset")
                    reset_ts = int(reset_header) if reset_header and reset_header.isdigit() else None
                    logger.warning("GitHub rate limit hit. Reset timestamp: %s", reset_ts)
                    raise GitHubRateLimitError(reset_timestamp=reset_ts)

                if response.status_code >= 500 and attempt < retries:
                    logger.warning("Transient GitHub 5xx error on %s, retrying...", path)
                    continue

                return response

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt < retries:
                    logger.warning("Connection failure to GitHub on %s (%s), retrying...", path, str(exc))
                    continue
                raise GitHubAPIError(f"GitHub connection timed out or failed: {str(exc)}", status_code=504)

        raise GitHubAPIError("GitHub API request failed after retries", status_code=502)

    async def get_current_user(self) -> dict[str, Any]:
        """Fetch authenticated GitHub user profile."""
        response = await self._request("GET", "/user")
        if response.status_code == 401:
            raise GitHubAPIError("GitHub token is invalid or expired", status_code=401)
        if response.status_code != 200:
            raise GitHubAPIError(f"Failed to fetch GitHub user: {response.text}", status_code=response.status_code)
        return response.json()

    async def list_repositories(
        self,
        page: int = 1,
        per_page: int = 30,
        sort: str = "updated",
    ) -> list[dict[str, Any]]:
        """List repositories accessible to the user with pagination."""
        params = {
            "page": max(1, page),
            "per_page": min(100, max(1, per_page)),
            "sort": sort,
            "visibility": "all",
            "affiliation": "owner,collaborator",
        }
        response = await self._request("GET", "/user/repos", params=params)
        if response.status_code != 200:
            raise GitHubAPIError(
                f"Failed to list GitHub repositories: {response.text}",
                status_code=response.status_code,
            )
        return response.json()

    async def get_repository_languages(self, owner: str, repo: str) -> dict[str, int]:
        """Fetch language byte breakdown for a repository."""
        response = await self._request("GET", f"/repos/{owner}/{repo}/languages")
        if response.status_code == 404:
            return {}
        if response.status_code != 200:
            logger.warning("Could not fetch languages for %s/%s: %s", owner, repo, response.text)
            return {}
        return response.json()

    async def get_repository_tree(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        """Fetch recursive file tree paths for a repository."""
        response = await self._request("GET", f"/repos/{owner}/{repo}/git/trees/{branch}", params={"recursive": "1"})
        if response.status_code != 200:
            logger.warning("Could not fetch git tree for %s/%s branch %s (status: %d)", owner, repo, branch, response.status_code)
            return []
        data = response.json()
        return data.get("tree", [])

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        file_path: str,
        ref: str = "main",
    ) -> str | None:
        """Fetch raw content of a text file from GitHub with size limits."""
        response = await self._request("GET", f"/repos/{owner}/{repo}/contents/{file_path}", params={"ref": ref})
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            logger.debug("File %s not accessible in %s/%s", file_path, owner, repo)
            return None

        data = response.json()
        if not isinstance(data, dict):
            return None

        # Check file size limit
        file_size = data.get("size", 0)
        if file_size > MAX_ANALYSIS_FILE_SIZE_BYTES:
            logger.info("Skipping large file %s (%d bytes)", file_path, file_size)
            return None

        content_encoded = data.get("content")
        if not content_encoded:
            return None

        try:
            decoded_bytes = base64.b64decode(content_encoded)
            return decoded_bytes.decode("utf-8", errors="ignore")
        except Exception as exc:
            logger.warning("Failed to decode file %s: %s", file_path, str(exc))
            return None
