"""Validation for user-supplied source locations."""

from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import HTTPException

from app.core.config import Settings, get_settings


def _is_public_address(host: str) -> bool:
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
    except socket.gaierror:
        return False

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            return False
    return bool(addresses)


def _extract_git_host(value: str) -> tuple[str, str]:
    if value.startswith("git@"):
        host, separator, path = value[4:].partition(":")
        if not separator or not host or not path:
            raise HTTPException(status_code=400, detail="Invalid SSH Git URL")
        return "ssh", host

    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "ssh"} or not parsed.hostname:
        raise HTTPException(
            status_code=400,
            detail="Sources must use HTTPS or SSH Git URLs",
        )
    if parsed.password or (parsed.scheme == "https" and parsed.username):
        raise HTTPException(
            status_code=400,
            detail="Credentials must be stored separately, not embedded in source URLs",
        )
    return parsed.scheme, parsed.hostname


def validate_source_location(value: str, settings: Settings | None = None) -> str:
    """Validate and normalize a source location before filesystem or network access."""
    settings = settings or get_settings()
    value = value.strip()
    if not value:
        raise HTTPException(status_code=400, detail="Source URL is required")

    if value.startswith(("https://", "ssh://", "git@", "http://", "git://")):
        _scheme, host = _extract_git_host(value)
        normalized_host = host.rstrip(".").lower()
        if normalized_host not in settings.source_host_allowlist:
            raise HTTPException(status_code=400, detail="Source host is not allowed")
        if not settings.allow_private_source_hosts and not _is_public_address(normalized_host):
            raise HTTPException(
                status_code=400,
                detail="Source host must resolve only to public network addresses",
            )
        return value

    if not settings.allow_local_sources or not settings.source_import_root:
        raise HTTPException(status_code=400, detail="Local filesystem sources are disabled")

    root = Path(settings.source_import_root).expanduser().resolve()
    candidate = Path(value).expanduser().resolve()
    if not candidate.is_relative_to(root):
        raise HTTPException(status_code=400, detail="Source path is outside the import root")
    if not candidate.is_dir():
        raise HTTPException(status_code=400, detail="Source path is not a directory")
    return str(candidate)
