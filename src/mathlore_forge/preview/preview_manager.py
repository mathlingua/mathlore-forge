"""Preview generation, GCS synchronization, and caching for Mathlore pull requests."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
from pathlib import Path
import subprocess
import urllib.parse
from typing import Any

import httpx

from mathlore_forge.storage.gcs_sync import _get_access_token, DEFAULT_BUCKET

logger = logging.getLogger(__name__)

# Ensure common web extensions have proper MIME types registered
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("text/html", ".html")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("application/wasm", ".wasm")


def build_pr_preview(
    workspace_dir: Path | str,
    pr_number: int,
    mlg_bin: str = "mlg",
) -> Path:
    """Compiles and exports the Mathlingua static documentation site for a PR.

    Configures `--base-path /previews/{pr_number}` so all static assets and links
    are correctly routed under the preview URL prefix.
    """
    ws = Path(workspace_dir).resolve()
    base_path = f"/previews/{pr_number}"
    cmd = [mlg_bin, "export", "--force", "--base-path", base_path]
    logger.info("Building PR #%s preview site in %s: %s", pr_number, ws, " ".join(cmd))

    proc = subprocess.run(cmd, cwd=str(ws), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        logger.warning(
            "mlg export failed for PR #%s (code %s):\nstdout: %s\nstderr: %s",
            pr_number,
            proc.returncode,
            proc.stdout,
            proc.stderr,
        )
        raise RuntimeError(f"mlg export failed: {proc.stderr or proc.stdout}")

    docs_dir = ws / "docs"
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"Export directory {docs_dir} was not created by `mlg export`.")

    logger.info("Successfully exported PR #%s preview site to %s", pr_number, docs_dir)
    return docs_dir


async def upload_preview_to_gcs(
    docs_dir: Path | str,
    pr_number: int,
    bucket_name: str | None = None,
) -> int:
    """Uploads the exported static site files to Google Cloud Storage under `previews/{pr_number}/`."""
    bucket = (bucket_name or os.getenv("GCS_DATA_BUCKET") or DEFAULT_BUCKET).strip()
    if not bucket:
        logger.warning("No GCS bucket configured; skipping preview upload.")
        return 0

    token = _get_access_token()
    if not token:
        logger.warning("Could not acquire Google auth token; skipping preview upload.")
        return 0

    docs_path = Path(docs_dir).resolve()
    files_to_upload: list[tuple[Path, str, str]] = []

    for root, _, files in os.walk(docs_path):
        for f in files:
            full = Path(root) / f
            rel = full.relative_to(docs_path).as_posix()
            object_name = f"previews/{pr_number}/{rel}"
            mime_type, _ = mimetypes.guess_type(str(full))
            content_type = mime_type or "application/octet-stream"
            files_to_upload.append((full, object_name, content_type))

    logger.info("Uploading %d files for PR #%s preview to gs://%s/previews/%s/", len(files_to_upload), pr_number, bucket, pr_number)

    uploaded_count = 0
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Upload in concurrency batches of 8
        sem = asyncio.Semaphore(8)

        async def _upload_file(full: Path, object_name: str, content_type: str) -> bool:
            nonlocal uploaded_count
            async with sem:
                encoded_name = urllib.parse.quote(object_name, safe="")
                url = f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o?uploadType=media&name={encoded_name}"
                data = full.read_bytes()
                try:
                    resp = await client.post(
                        url,
                        headers={**headers, "Content-Type": content_type},
                        content=data,
                    )
                    if resp.is_success:
                        uploaded_count += 1
                        return True
                    else:
                        logger.warning("Failed to upload %s: %s %s", object_name, resp.status_code, resp.text)
                except Exception as exc:
                    logger.warning("Error uploading %s: %s", object_name, exc)
                return False

        tasks = [_upload_file(full, name, ctype) for full, name, ctype in files_to_upload]
        await asyncio.gather(*tasks)

    logger.info("Completed upload: %d/%d files uploaded for PR #%s preview", uploaded_count, len(files_to_upload), pr_number)
    return uploaded_count


async def get_preview_file(
    pr_number: int,
    file_path: str,
    bucket_name: str | None = None,
) -> tuple[bytes | None, str]:
    """Retrieves a preview file, utilizing local disk cache with GCS fallback.

    Returns:
        (content_bytes, content_type) or (None, "") if not found.
    """
    clean_path = file_path.strip("/")
    if not clean_path or clean_path.endswith("/"):
        clean_path = f"{clean_path}index.html" if clean_path else "index.html"

    mime_type, _ = mimetypes.guess_type(clean_path)
    content_type = mime_type or "application/octet-stream"

    # 1. Check local cache
    cache_dir = Path("/tmp/mathlore_previews") / str(pr_number)
    cached_file = cache_dir / clean_path
    if cached_file.is_file():
        return cached_file.read_bytes(), content_type

    # 2. Check GCS
    bucket = (bucket_name or os.getenv("GCS_DATA_BUCKET") or DEFAULT_BUCKET).strip()
    if not bucket:
        return None, ""

    token = _get_access_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    object_name = f"previews/{pr_number}/{clean_path}"
    encoded_name = urllib.parse.quote(object_name, safe="")
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{encoded_name}?alt=media"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.content
                # Cache locally for subsequent fast hits
                try:
                    cached_file.parent.mkdir(parents=True, exist_ok=True)
                    cached_file.write_bytes(data)
                except Exception:
                    pass
                return data, content_type
            elif resp.status_code == 404 and clean_path != "404.html":
                # Fallback to 404.html if available
                return await get_preview_file(pr_number, "404.html", bucket_name=bucket)
    except Exception as exc:
        logger.warning("Error fetching preview file %s from GCS: %s", object_name, exc)

    return None, ""


def get_preview_url(
    pr_number: int,
    base_url: str = "https://mathlore-forge-web-bx7vyixa6a-uc.a.run.app",
) -> str:
    """Returns the canonical URL for viewing the rendered PR preview."""
    return f"{base_url.rstrip('/')}/previews/{pr_number}/"
