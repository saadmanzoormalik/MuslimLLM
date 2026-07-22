from __future__ import annotations

import hashlib
import ipaddress
import os
import socket
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx


@dataclass
class ValidationResult:
    valid: bool
    code: str = "ok"
    details: dict = field(default_factory=dict)


@dataclass
class DownloadResult:
    path: Path
    sha256: str
    bytes_downloaded: int
    content_type: str


def _approved_hosts() -> set[str]:
    configured = os.getenv("CONTEXT_SYNC_APPROVED_DOWNLOAD_HOSTS", "openai.com,chatgpt.com,oaistatic.com")
    return {item.strip().lower().lstrip(".") for item in configured.split(",") if item.strip()}


def _host_allowed(host: str) -> bool:
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in _approved_hosts())


def _is_public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return not (address.is_private or address.is_loopback or address.is_link_local or address.is_multicast or address.is_reserved or address.is_unspecified)


def validate_export_url(url: str) -> ValidationResult:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https":
            return ValidationResult(False, "https_required")
        if not host or parsed.username or parsed.password:
            return ValidationResult(False, "invalid_url")
        if not _host_allowed(host):
            return ValidationResult(False, "hostname_not_approved")
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        except socket.gaierror:
            return ValidationResult(False, "dns_resolution_failed")
        if not addresses or any(not _is_public_address(address) for address in addresses):
            return ValidationResult(False, "private_network_blocked")
        return ValidationResult(True, details={"hostname": host})
    except (ValueError, ipaddress.AddressValueError):
        return ValidationResult(False, "invalid_url")


async def stream_secure_download(url: str, destination: Path) -> DownloadResult:
    maximum = int(os.getenv("CONTEXT_SYNC_MAX_ARCHIVE_BYTES", str(2 * 1024 * 1024 * 1024)))
    redirect_limit = int(os.getenv("CONTEXT_SYNC_DOWNLOAD_REDIRECT_LIMIT", "4"))
    current_url = url
    digest = hashlib.sha256()
    downloaded = 0
    content_type = ""
    destination.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10), follow_redirects=False) as client:
        for redirect_count in range(redirect_limit + 1):
            validation = validate_export_url(current_url)
            if not validation.valid:
                raise ValueError(validation.code)
            request = client.build_request("GET", current_url, headers={"Accept": "application/zip,application/octet-stream"})
            response = await client.send(request, stream=True)
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                await response.aclose()
                if not location or redirect_count >= redirect_limit:
                    raise ValueError("redirect_limit_exceeded")
                current_url = urljoin(current_url, location)
                continue
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if content_type and content_type not in {"application/zip", "application/x-zip-compressed", "application/octet-stream"}:
                await response.aclose()
                raise ValueError("unexpected_content_type")
            try:
                with destination.open("wb") as handle:
                    async for chunk in response.aiter_bytes(1024 * 1024):
                        downloaded += len(chunk)
                        if downloaded > maximum:
                            raise ValueError("archive_too_large")
                        digest.update(chunk)
                        handle.write(chunk)
            except Exception:
                destination.unlink(missing_ok=True)
                raise
            finally:
                await response.aclose()
            break
        else:
            raise ValueError("redirect_limit_exceeded")

    archive_validation = validate_downloaded_archive(destination)
    if not archive_validation.valid:
        destination.unlink(missing_ok=True)
        raise ValueError(archive_validation.code)
    return DownloadResult(destination, digest.hexdigest(), downloaded, content_type)


def validate_downloaded_archive(path: Path) -> ValidationResult:
    maximum = int(os.getenv("CONTEXT_SYNC_MAX_ARCHIVE_BYTES", str(2 * 1024 * 1024 * 1024)))
    try:
        size = path.stat().st_size
        if size <= 0:
            return ValidationResult(False, "empty_archive")
        if size > maximum:
            return ValidationResult(False, "archive_too_large")
        with path.open("rb") as handle:
            if handle.read(4) not in {b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"}:
                return ValidationResult(False, "invalid_zip_signature")
        return ValidationResult(True, details={"bytes": size})
    except OSError:
        return ValidationResult(False, "archive_unreadable")
