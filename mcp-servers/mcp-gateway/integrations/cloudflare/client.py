"""Upload a bounded static page or small site to a configured workspace Pages project.

The asset protocol and hash match Cloudflare Wrangler's Pages uploader.
Credentials never enter an MCP tool argument or result.
"""
import asyncio
import base64
import binascii
import json
import os
import re
from pathlib import PurePosixPath

import blake3
import httpx

from policy import Denied, credential

ACCOUNT_ID = "1e68ce9114426cd4bf6c4129400ea0c5"
API = "https://api.cloudflare.com/client/v4"
PROJECT_NAME = re.compile(r"[a-z][a-z0-9-]{0,62}\Z")
CONTENT_TYPES = {
    ".css": "text/css",
    ".gif": "image/gif",
    ".html": "text/html",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".js": "text/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}
TEXT_TYPES = {".html", ".js", ".json"}
MAX_HTML = 2 * 1024 * 1024  # index.html and each extra .html, .js or .json file
MAX_TOTAL = 8 * 1024 * 1024
MAX_ASSETS = 64
# Cloudflare truncates branch aliases to 28 characters; refuse longer names so two never collide.
MAX_BRANCH = 28
PAGE_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def _file_hash(data: bytes, path: str) -> str:
    # Wrangler: blake3(base64(file bytes) + filename extension).slice(0, 32).
    extension = PurePosixPath(path).suffix.removeprefix(".")
    return blake3.blake3(base64.b64encode(data) + extension.encode()).hexdigest()[:32]


def _files(html: str, assets: list[dict]) -> dict[str, tuple[bytes, str]]:
    if not isinstance(html, str) or not html.strip():
        raise Denied("HTML is required")
    html_bytes = html.encode("utf-8")
    if len(html_bytes) > MAX_HTML:
        raise Denied("HTML exceeds the 2 MiB limit")
    if not isinstance(assets, list) or len(assets) > MAX_ASSETS:
        raise Denied(f"At most {MAX_ASSETS} extra files are allowed")
    files = {"index.html": (html_bytes, "text/html")}
    total = len(html_bytes)
    for asset in assets:
        if not isinstance(asset, dict):
            raise Denied("Invalid asset")
        path = asset.get("path")
        encoded = asset.get("base64")
        if not isinstance(path, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", path):
            raise Denied("Asset paths must be simple relative paths")
        parts = PurePosixPath(path).parts
        if any(part in (".", "..") or part.startswith(".") for part in parts) or path in files:
            raise Denied("Duplicate or hidden asset path")
        # _worker.js, _headers, _redirects, _routes.json and functions/ control Pages behaviour.
        if parts[0].startswith("_") or parts[0].lower() == "functions":
            raise Denied("Pages control files are not allowed")
        suffix = PurePosixPath(path).suffix.lower()
        content_type = CONTENT_TYPES.get(suffix)
        if content_type is None or not isinstance(encoded, str):
            raise Denied("Only HTML, JavaScript, JSON, CSS and image files are allowed")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise Denied("Asset base64 is invalid") from exc
        if suffix in TEXT_TYPES and len(data) > MAX_HTML:
            raise Denied(f"{path} exceeds the 2 MiB limit for a text file")
        total += len(data)
        if total > MAX_TOTAL:
            raise Denied("Upload exceeds the 8 MiB limit")
        files[path] = (data, content_type)
    return files


def _result(response: httpx.Response):
    try:
        body = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Cloudflare returned HTTP {response.status_code}") from exc
    if response.status_code >= 400 or not body.get("success", False):
        errors = body.get("errors") or []
        code = errors[0].get("code") if errors and isinstance(errors[0], dict) else None
        raise RuntimeError(f"Cloudflare request failed (HTTP {response.status_code}, code {code})")
    return body.get("result")


def branch_name(pipeline_id: int, page: str | None = None) -> str:
    if isinstance(pipeline_id, bool) or not isinstance(pipeline_id, int) or not 1 <= pipeline_id <= 999999999:
        raise Denied("Pipeline ID must be a positive number")
    if page is None or page == "":
        return f"pipeline-{pipeline_id}"
    if not isinstance(page, str) or not PAGE_NAME.fullmatch(page):
        raise Denied("Page name must be lowercase letters and digits separated by single hyphens")
    branch = f"pipeline-{pipeline_id}-{page}"
    if len(branch) > MAX_BRANCH:
        raise Denied(f"pipeline-<ID>-<page> must be at most {MAX_BRANCH} characters")
    return branch


async def publish(pipeline_id: int, html: str, assets: list[dict], project: str, page: str | None = None) -> dict:
    branch = branch_name(pipeline_id, page)
    if not isinstance(project, str) or not PROJECT_NAME.fullmatch(project):
        raise Denied("Cloudflare project is not configured")
    files = _files(html, assets)
    api_token = credential("CLOUDFLARE_PAGES_API_TOKEN")
    account_headers = {"Authorization": f"Bearer {api_token}"}
    project_path = f"/accounts/{ACCOUNT_ID}/pages/projects/{project}"
    async with httpx.AsyncClient(base_url=API, timeout=30, trust_env=False, follow_redirects=False) as client:
        response = await client.get(f"{project_path}/upload-token", headers=account_headers)
        jwt = _result(response)["jwt"]
        upload_headers = {"Authorization": f"Bearer {jwt}"}
        hashes = {path: _file_hash(data, path) for path, (data, _) in files.items()}
        response = await client.post("/pages/assets/check-missing", headers=upload_headers,
                                     json={"hashes": list(hashes.values())})
        missing = set(_result(response))
        payload = [
            {"key": hashes[path], "value": base64.b64encode(data).decode("ascii"),
             "metadata": {"contentType": content_type}, "base64": True}
            for path, (data, content_type) in files.items() if hashes[path] in missing
        ]
        if payload:
            response = await client.post("/pages/assets/upload", headers=upload_headers, json=payload)
            _result(response)
        response = await client.post("/pages/assets/upsert-hashes", headers=upload_headers,
                                     json={"hashes": list(hashes.values())})
        _result(response)
        manifest = {f"/{path}": file_hash for path, file_hash in hashes.items()}
        response = await client.post(
            f"{project_path}/deployments", headers=account_headers,
            files={
                "branch": (None, branch),
                "manifest": (None, json.dumps(manifest)),
                "commit_message": (None, f"Publish {branch} for Pipeline {pipeline_id}"),
            },
        )
        deployment = _result(response)
        deployment_id = deployment["id"]
        for attempt in range(12):
            response = await client.get(f"{project_path}/deployments/{deployment_id}", headers=account_headers)
            deployment = _result(response)
            stage = deployment.get("latest_stage") or {}
            if stage.get("status") == "success":
                return {"pipeline_id": pipeline_id, "branch": branch, "url": f"https://{branch}.{project}.pages.dev/",
                        "deployment_id": deployment_id, "file_count": len(files)}
            if stage.get("status") in ("failure", "canceled"):
                raise RuntimeError(f"Cloudflare deployment {deployment_id} {stage['status']}")
            if attempt < 11:
                await asyncio.sleep(2)
        raise RuntimeError(f"Cloudflare deployment {deployment_id} is still processing")
