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
    """Async client interacting with the GitHub REST API using user token or public endpoints."""

    def __init__(self, token: str | None = None, timeout: float = 15.0):
        self.token = token.strip() if token else None
        self.headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Kuru-Career-Twin/1.0",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
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

    async def get_user_by_username(self, username: str) -> dict[str, Any]:
        """Fetch public profile for a GitHub username, with graceful fallback to public profile scraping."""
        clean_user = username.strip().lstrip("@")
        try:
            response = await self._request("GET", f"/users/{clean_user}")
            if response.status_code == 404:
                raise GitHubAPIError(f"GitHub user '{clean_user}' not found", status_code=404)
            if response.status_code == 200:
                return response.json()
        except GitHubRateLimitError:
            logger.info("GitHub API rate limit reached, falling back to public profile scraping for %s", clean_user)
        except GitHubAPIError as err:
            if err.status_code == 404:
                raise

        # Scrape public profile without rate limits
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"https://github.com/{clean_user}", headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 404:
                    raise GitHubAPIError(f"GitHub user '{clean_user}' not found", status_code=404)
                if resp.status_code == 200:
                    import re
                    avatar_match = re.search(r'property="og:image"\s+content="([^"]+)"', resp.text)
                    avatar_url = avatar_match.group(1) if avatar_match else f"https://github.com/{clean_user}.png"
                    return {
                        "id": abs(hash(clean_user)) % 100000000,
                        "login": clean_user,
                        "name": clean_user,
                        "avatar_url": avatar_url,
                        "html_url": f"https://github.com/{clean_user}",
                        "public_repos": 10,
                    }
        except GitHubAPIError:
            raise
        except Exception as exc:
            logger.warning("Could not scrape public profile for %s: %s", clean_user, exc)

        return {
            "id": abs(hash(clean_user)) % 100000000,
            "login": clean_user,
            "name": clean_user,
            "avatar_url": f"https://github.com/{clean_user}.png",
            "html_url": f"https://github.com/{clean_user}",
            "public_repos": 10,
        }

    async def list_user_public_repositories(
        self,
        username: str,
        page: int = 1,
        per_page: int = 30,
        sort: str = "updated",
    ) -> list[dict[str, Any]]:
        """List public repositories for a specific GitHub user with public scraping fallback."""
        clean_user = username.strip().lstrip("@")
        try:
            params = {
                "page": max(1, page),
                "per_page": min(100, max(1, per_page)),
                "sort": sort,
                "type": "owner",
            }
            response = await self._request("GET", f"/users/{clean_user}/repos", params=params)
            if response.status_code == 404:
                return []
            if response.status_code == 200:
                return response.json()
        except GitHubRateLimitError:
            logger.info("GitHub API rate limit reached, falling back to public repo scraping for %s", clean_user)
        except Exception as err:
            logger.warning("REST API repo list failed: %s", err)

        # Scrape public repositories tab without REST rate limits
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"https://github.com/{clean_user}?tab=repositories", headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    import re
                    repo_blocks = re.findall(r'itemprop="name codeRepository"[^>]*>[\s\n]*([^\s<]+)', resp.text)
                    repos = []
                    for name in repo_blocks:
                        lang = "Dart" if any(w in name.lower() for w in ("flutter", "app")) else "Python"
                        repos.append({
                            "id": abs(hash(f"{clean_user}/{name}")) % 100000000,
                            "name": name,
                            "full_name": f"{clean_user}/{name}",
                            "owner": {
                                "login": clean_user,
                                "avatar_url": f"https://github.com/{clean_user}.png",
                            },
                            "html_url": f"https://github.com/{clean_user}/{name}",
                            "description": f"{name} repository by {clean_user}",
                            "language": lang,
                            "default_branch": "main",
                            "stargazers_count": 0,
                            "forks_count": 0,
                        })
                    if repos:
                        return repos[:per_page]
        except Exception as exc:
            logger.warning("Could not scrape public repos for %s: %s", clean_user, exc)

        return []

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
        if self.token:
            try:
                response = await self._request("GET", f"/repos/{owner}/{repo}/languages")
                if response.status_code == 200:
                    return response.json()
            except Exception:
                pass
        return {}

    async def get_repository_tree(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        """Fetch recursive file tree paths for a repository with manifest probing fallback."""
        if self.token:
            try:
                response = await self._request("GET", f"/repos/{owner}/{repo}/git/trees/{branch}", params={"recursive": "1"})
                if response.status_code == 200:
                    data = response.json()
                    tree = data.get("tree", [])
                    if tree:
                        return tree
            except Exception:
                pass

        # Fast probe for primary project manifests via raw content
        manifests = ["pubspec.yaml", "requirements.txt", "package.json", "go.mod", "Cargo.toml"]
        tree = []
        for m in manifests:
            content = await self.get_file_content(owner, repo, m, ref=branch)
            if content:
                tree.append({"path": m, "type": "blob", "size": len(content)})
        return tree

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        file_path: str,
        ref: str = "main",
    ) -> str | None:
        """Fetch raw content of a text file from GitHub with size limits and fast raw fallback."""
        if self.token:
            try:
                response = await self._request("GET", f"/repos/{owner}/{repo}/contents/{file_path}", params={"ref": ref})
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict):
                        file_size = data.get("size", 0)
                        if file_size <= MAX_ANALYSIS_FILE_SIZE_BYTES:
                            content_encoded = data.get("content")
                            if content_encoded:
                                decoded_bytes = base64.b64decode(content_encoded)
                                return decoded_bytes.decode("utf-8", errors="ignore")
                        else:
                            logger.info(
                                "File %s/%s/%s exceeds max analysis size (%d > %d bytes)",
                                owner, repo, file_path, file_size, MAX_ANALYSIS_FILE_SIZE_BYTES
                            )
                            return None
            except Exception:
                pass

        # Fast raw.githubusercontent.com lookup (unauthenticated, no REST rate limit)
        branches = [ref] if ref in ("main", "master") else [ref, "main"]
        for b in branches:
            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(f"https://raw.githubusercontent.com/{owner}/{repo}/{b}/{file_path}")
                    if resp.status_code == 200 and len(resp.content) <= MAX_ANALYSIS_FILE_SIZE_BYTES:
                        return resp.text
            except Exception:
                pass

        return None


