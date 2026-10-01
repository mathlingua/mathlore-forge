"""Automatic synchronization between local SQLite database and Google Cloud Storage."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

DEFAULT_BUCKET = os.getenv("GCS_DATA_BUCKET", "mathlore-forge-data-storage").strip()
DB_OBJECT_NAME = "mathlore_forge.sqlite"


def _get_access_token() -> str | None:
    try:
        import google.auth
        from google.auth.transport.requests import Request

        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(Request())
        return creds.token
    except Exception as exc:
        logger.debug("Could not acquire Google auth token for GCS sync: %s", exc)
        return None


def download_db_from_gcs(target_path: Path | str, bucket: str | None = None) -> bool:
    """Downloads the SQLite database from GCS to local disk."""
    bucket_name = (bucket or os.getenv("GCS_DATA_BUCKET") or DEFAULT_BUCKET).strip()
    if not bucket_name:
        return False

    token = _get_access_token()
    if not token:
        logger.info("GCS sync: No Google access token available; skipping DB download.")
        return False

    target = Path(target_path).resolve()
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o/{DB_OBJECT_NAME}?alt=media"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            logger.info(
                "Successfully restored database from gs://%s/%s (%d bytes)",
                bucket_name,
                DB_OBJECT_NAME,
                len(data),
            )
            return True
    except urllib.error.HTTPError as err:
        if err.code == 404:
            logger.info("No existing database found in gs://%s/%s; starting fresh.", bucket_name, DB_OBJECT_NAME)
        else:
            logger.warning("HTTP error downloading DB from gs://%s/%s: %s", bucket_name, DB_OBJECT_NAME, err)
        return False
    except Exception as exc:
        logger.warning("Failed downloading DB from gs://%s/%s: %s", bucket_name, DB_OBJECT_NAME, exc)
        return False


def upload_db_to_gcs(source_path: Path | str, bucket: str | None = None) -> bool:
    """Uploads local SQLite database file to GCS."""
    bucket_name = (bucket or os.getenv("GCS_DATA_BUCKET") or DEFAULT_BUCKET).strip()
    if not bucket_name:
        return False

    source = Path(source_path).resolve()
    if not source.exists():
        logger.debug("Local database file %s does not exist; skipping upload.", source)
        return False

    token = _get_access_token()
    if not token:
        logger.debug("GCS sync: No Google access token available; skipping DB upload.")
        return False

    try:
        content = source.read_bytes()
        url = f"https://storage.googleapis.com/upload/storage/v1/b/{bucket_name}/o?uploadType=media&name={DB_OBJECT_NAME}"
        req = urllib.request.Request(
            url,
            data=content,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status in (200, 201):
                logger.info(
                    "Successfully synced database to gs://%s/%s (%d bytes)",
                    bucket_name,
                    DB_OBJECT_NAME,
                    len(content),
                )
                return True
    except Exception as exc:
        logger.warning("Failed uploading DB to gs://%s/%s: %s", bucket_name, DB_OBJECT_NAME, exc)
        return False
    return False


def sync_db_to_gcs_now(db_path: str = "mathlore_forge.sqlite") -> None:
    """Non-blocking or synchronous trigger to upload database to GCS."""
    try:
        upload_db_to_gcs(db_path)
    except Exception as exc:
        logger.warning("Error in sync_db_to_gcs_now: %s", exc)
