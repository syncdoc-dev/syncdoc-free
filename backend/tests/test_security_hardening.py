"""Regression tests for security-sensitive access boundaries."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, settings
from app.core.security import decrypt_token, encrypt_token
from app.core.source_security import validate_source_location
from app.models.credential import SourceCredential
from app.models.organization import Organization
from app.models.project import Project
from app.models.source import Source
from app.services.credentials import CredentialManager
from app.tasks.sync import _coerce_utc


@pytest.mark.asyncio
async def test_database_browser_is_not_exposed(async_client):
    response = await async_client.get("/api/admin/db/tables")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_self_registered_users_receive_isolated_orgs(async_client):
    original = settings.allow_self_register
    settings.allow_self_register = True
    try:
        first = await async_client.post(
            "/api/auth/register",
            json={
                "login": "security-user-one",
                "email": "security-one@example.com",
                "password": "correct horse battery staple",
            },
        )
        second = await async_client.post(
            "/api/auth/register",
            json={
                "login": "security-user-two",
                "email": "security-two@example.com",
                "password": "correct horse battery staple",
            },
        )
    finally:
        settings.allow_self_register = original

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["user"]["role"] == "owner"
    assert second.json()["user"]["role"] == "owner"
    assert first.json()["user"]["organization_id"] != second.json()["user"]["organization_id"]


def test_local_source_must_be_inside_explicit_root(tmp_path):
    root = tmp_path / "imports"
    allowed = root / "repo"
    denied = tmp_path / "private"
    allowed.mkdir(parents=True)
    denied.mkdir()
    config = Settings(
        allow_local_sources=True,
        source_import_root=str(root),
    )

    assert validate_source_location(str(allowed), config) == str(allowed.resolve())
    with pytest.raises(Exception):
        validate_source_location(str(denied), config)


def test_remote_source_rejects_unapproved_hosts(monkeypatch):
    config = Settings(allowed_source_hosts="github.com")
    monkeypatch.setattr(
        "app.core.source_security.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("140.82.121.3", 0))],
    )

    assert (
        validate_source_location("https://github.com/example/repo.git", config)
        == "https://github.com/example/repo.git"
    )
    assert (
        validate_source_location("ssh://git@github.com/example/repo.git", config)
        == "ssh://git@github.com/example/repo.git"
    )
    with pytest.raises(Exception):
        validate_source_location("https://example.invalid/repo.git", config)


def test_private_allowlisted_source_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setattr(
        "app.core.source_security.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("10.0.0.10", 0))],
    )
    url = "https://git.internal.example/team/repo.git"

    with pytest.raises(Exception):
        validate_source_location(
            url,
            Settings(allowed_source_hosts="git.internal.example"),
        )

    assert (
        validate_source_location(
            url,
            Settings(
                allowed_source_hosts="git.internal.example",
                allow_private_source_hosts=True,
            ),
        )
        == url
    )


@pytest.mark.asyncio
async def test_credential_delete_is_scoped_to_source(test_db):
    session_factory = async_sessionmaker(
        test_db,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        org = Organization(id=str(uuid.uuid4()), name="Credential Test Org")
        project = Project(id=str(uuid.uuid4()), organization_id=org.id, name="General")
        first_source = Source(
            id="source-one",
            type="git",
            url="https://github.com/example/one.git",
            organization_id=org.id,
            project_id=project.id,
        )
        second_source = Source(
            id="source-two",
            type="git",
            url="https://github.com/example/two.git",
            organization_id=org.id,
            project_id=project.id,
        )
        credential = SourceCredential(
            id="credential-one",
            source_id=second_source.id,
            credential_type="token",
            encrypted_value=encrypt_token("secret"),
        )
        session.add_all([org, project, first_source, second_source, credential])
        await session.commit()

        deleted = await CredentialManager.delete_credential(
            session,
            first_source.id,
            credential.id,
        )
        assert deleted is False
        assert await session.get(SourceCredential, credential.id) is not None


def test_legacy_credentials_remain_decryptable_with_new_key():
    original_key = settings.credential_encryption_key
    settings.credential_encryption_key = None
    encrypted = encrypt_token("legacy-secret")
    settings.credential_encryption_key = "new-encryption-key-with-at-least-32-bytes"
    try:
        assert decrypt_token(encrypted) == "legacy-secret"
    finally:
        settings.credential_encryption_key = original_key


def test_auto_sync_timestamps_are_normalized_to_utc():
    naive = datetime(2026, 6, 10, 12, 0, 0)
    aware = datetime(2026, 6, 10, 13, 0, 0, tzinfo=timezone.utc)

    assert _coerce_utc(naive) == datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
    assert _coerce_utc(aware) == aware
    assert _coerce_utc(None) is None
