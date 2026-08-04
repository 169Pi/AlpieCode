"""
GitHub integration for AlpieCode — browse repos, read issues, search code.

Uses the GitHub REST API (v3) via urllib (zero extra dependencies).
Supports unauthenticated access (60 req/hr) or authenticated via
GITHUB_TOKEN env var (5000 req/hr).
"""

import json
import os
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── API helpers ───────────────────────────────────────────────────────

API_BASE = "https://api.github.com"


def _github_headers() -> dict:
    """Build request headers, using GITHUB_TOKEN if available."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AlpieCode/0.5.0",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _api_get(endpoint: str, params: dict = None) -> Any:
    """Make a GET request to the GitHub API."""
    url = f"{API_BASE}{endpoint}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        if query:
            url += f"?{query}"

    req = urllib.request.Request(url, headers=_github_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        if e.code == 403 and "rate limit" in error_body.lower():
            return {"error": "GitHub API rate limit exceeded. Set GITHUB_TOKEN env var for 5000 req/hr."}
        if e.code == 404:
            return {"error": f"Not found: {endpoint}"}
        return {"error": f"GitHub API error {e.code}: {error_body[:300]}"}
    except Exception as e:
        return {"error": f"Request failed: {e}"}


# ── Repository info ───────────────────────────────────────────────────

def fetch_repo_info(owner: str, repo: str) -> str:
    """Fetch basic repository information."""
    data = _api_get(f"/repos/{owner}/{repo}")
    if isinstance(data, dict) and "error" in data:
        return json.dumps(data)

    info = {
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "default_branch": data.get("default_branch"),
        "topics": data.get("topics", []),
        "license": data.get("license", {}).get("spdx_id") if data.get("license") else None,
        "url": data.get("html_url"),
    }
    return json.dumps(info, indent=2)


def fetch_repo_tree(owner: str, repo: str, path: str = "") -> str:
    """Fetch directory listing from a GitHub repo."""
    endpoint = f"/repos/{owner}/{repo}/contents/{path}" if path else f"/repos/{owner}/{repo}/contents"
    data = _api_get(endpoint)
    if isinstance(data, dict) and "error" in data:
        return json.dumps(data)

    if isinstance(data, list):
        entries = []
        for item in data[:100]:  # Cap at 100 entries
            entry = {
                "name": item.get("name"),
                "type": item.get("type"),  # "file" or "dir"
                "size": item.get("size"),
                "path": item.get("path"),
            }
            entries.append(entry)
        return json.dumps(entries, indent=2)

    # Single file — return content
    if isinstance(data, dict) and data.get("content"):
        import base64
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return f"File: {data.get('path')}\nSize: {data.get('size')} bytes\n\n{content}"

    return json.dumps(data, indent=2)


# ── Issues & Pull Requests ────────────────────────────────────────────

def fetch_issues(owner: str, repo: str, state: str = "open",
                 max_results: int = 10) -> str:
    """Fetch issues list from a GitHub repo."""
    data = _api_get(f"/repos/{owner}/{repo}/issues", {
        "state": state,
        "per_page": min(max_results, 30),
        "sort": "updated",
        "direction": "desc",
    })
    if isinstance(data, dict) and "error" in data:
        return json.dumps(data)

    issues = []
    for item in data[:max_results]:
        issue = {
            "number": item.get("number"),
            "title": item.get("title"),
            "state": item.get("state"),
            "labels": [l.get("name") for l in item.get("labels", [])],
            "user": item.get("user", {}).get("login"),
            "comments": item.get("comments"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "is_pull_request": "pull_request" in item,
            "url": item.get("html_url"),
        }
        issues.append(issue)
    return json.dumps(issues, indent=2)


def fetch_issue_detail(owner: str, repo: str, issue_number: int) -> str:
    """Fetch full issue details including body and comments."""
    # Fetch issue body
    data = _api_get(f"/repos/{owner}/{repo}/issues/{issue_number}")
    if isinstance(data, dict) and "error" in data:
        return json.dumps(data)

    result = {
        "number": data.get("number"),
        "title": data.get("title"),
        "state": data.get("state"),
        "user": data.get("user", {}).get("login"),
        "labels": [l.get("name") for l in data.get("labels", [])],
        "body": data.get("body", "")[:3000],  # Cap body at 3000 chars
        "created_at": data.get("created_at"),
        "url": data.get("html_url"),
    }

    # Fetch comments
    if data.get("comments", 0) > 0:
        comments_data = _api_get(f"/repos/{owner}/{repo}/issues/{issue_number}/comments", {
            "per_page": 10,
        })
        if isinstance(comments_data, list):
            result["comments"] = [
                {
                    "user": c.get("user", {}).get("login"),
                    "body": c.get("body", "")[:1000],  # Cap each comment
                    "created_at": c.get("created_at"),
                }
                for c in comments_data[:10]
            ]

    return json.dumps(result, indent=2)


# ── Search ────────────────────────────────────────────────────────────

def search_repos(query: str, max_results: int = 5) -> str:
    """Search GitHub repositories by keyword."""
    data = _api_get("/search/repositories", {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": min(max_results, 10),
    })
    if isinstance(data, dict) and "error" in data:
        return json.dumps(data)

    repos = []
    for item in data.get("items", [])[:max_results]:
        repos.append({
            "full_name": item.get("full_name"),
            "description": item.get("description"),
            "stars": item.get("stargazers_count"),
            "language": item.get("language"),
            "url": item.get("html_url"),
        })
    return json.dumps(repos, indent=2)


# ── Clone ─────────────────────────────────────────────────────────────

def clone_repo(repo_url: str, workdir: Path, branch: str = None) -> str:
    """Clone a GitHub repository into the working directory."""
    # Normalize URL
    if not repo_url.startswith("http"):
        repo_url = f"https://github.com/{repo_url}.git"
    elif not repo_url.endswith(".git"):
        repo_url = repo_url.rstrip("/") + ".git"

    # Extract repo name for the directory
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    clone_dir = workdir / repo_name

    if clone_dir.exists():
        return f"Repository already exists at {repo_name}/. Use read_file and list_files to explore it."

    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([repo_url, str(clone_dir)])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            # Get a quick summary of what was cloned
            file_count = sum(1 for _ in clone_dir.rglob("*") if _.is_file())
            return (
                f"Successfully cloned {repo_url} into {repo_name}/\n"
                f"Files: {file_count}\n"
                f"Use list_files and read_file to explore the repository."
            )
        else:
            return f"Clone failed: {result.stderr[:500]}"
    except subprocess.TimeoutExpired:
        return "Clone timed out after 120s. The repository may be too large."
    except Exception as e:
        return f"Clone error: {e}"
