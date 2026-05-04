"""Pytest configuration and fixtures"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.project import Project
from app.models.user import User


@pytest.fixture
async def test_db():
    """Create an in-memory SQLite database for testing"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def async_client(test_db):
    """Create a test client with mocked database"""

    session_factory = async_sessionmaker(test_db, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(test_db):
    """Create a user + org membership and return auth headers."""
    session_factory = async_sessionmaker(test_db, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        org = Organization(id=str(uuid.uuid4()), name="Test Org")
        project = Project(id=str(uuid.uuid4()), organization_id=org.id, name="General")
        user = User(
            login="tester",
            email="tester@example.com",
            name="Test User",
            password_hash="x",
            auth_provider="local",
        )
        session.add_all([org, project, user])
        await session.flush()

        membership = OrganizationMembership(
            user_id=user.id,
            organization_id=org.id,
            role="owner",
        )
        session.add(membership)
        await session.commit()

        token = create_access_token(
            {
                "sub": str(user.id),
                "login": user.login,
                "org_id": membership.organization_id,
                "role": membership.role,
            }
        )

    return {"Authorization": f"Bearer {token}"}
