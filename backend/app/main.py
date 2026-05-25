"""FastAPI application entry point"""

import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import (
    admin,
    analytics,
    api_keys,
    capabilities,
    config,
    credentials,
    drift,
    graph,
    health,
    license,
    organizations,
    owner_explorer,
    pages,
    projects,
    search,
    settings,
    sources,
    sync_events,
    workflow,
)
from app.api.auth import router as auth_router
from app.core.config import get_settings
from app.core.database import get_session_factory, init_db
from app.core.rbac import ensure_membership
from app.core.security import hash_password
from app.models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    print("🚀 Starting SyncDoc API")
    await init_db()

    # Seed demo user when in demo mode
    settings = get_settings()
    if settings.demo_mode:
        # Read dynamic credentials from file if available
        demo_creds_file = os.environ.get("DEMO_STATE_DIR", "/demo-state") + "/creds.json"
        demo_username = settings.demo_username
        demo_password = settings.demo_password
        if os.path.exists(demo_creds_file):
            try:
                with open(demo_creds_file) as f:
                    creds = json.load(f)
                demo_username = creds.get("username", demo_username)
                demo_password = creds.get("password", demo_password)
                print(f"🎨 Demo mode — using dynamic credentials for {demo_username}")
            except Exception as exc:
                print(f"⚠️  Could not read demo creds file: {exc}")

        print(f"🎨 Demo mode active — ensuring demo user exists ({demo_username})")
        async with get_session_factory()() as db:
            result = await db.execute(select(User).where(User.login == demo_username))
            existing = result.scalar_one_or_none()
            if not existing:
                user = User(
                    login=demo_username,
                    email=f"{demo_username}@demo.syncdoc.dev",
                    name="Demo User",
                    password_hash=hash_password(demo_password),
                    auth_provider="local",
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                # Ensure org membership so login works immediately
                await ensure_membership(db, user.id)
                print(f"✅ Created demo user: {demo_username}")
            else:
                print(f"✅ Demo user already exists: {demo_username}")

    yield
    # Shutdown
    print("🛑 Shutting down SyncDoc API")


# Create FastAPI app
_settings = get_settings()
app = FastAPI(
    title="SyncDoc API",
    description="Infrastructure-Aware Living Documentation",
    version=_settings.app_version,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", _settings.frontend_url],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(api_keys.router, prefix="/api", tags=["api_keys"])
app.include_router(capabilities.router, prefix="/api", tags=["capabilities"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(credentials.router, prefix="/api", tags=["credentials"])
app.include_router(license.router, prefix="/api", tags=["license"])
app.include_router(pages.router, prefix="/api/pages", tags=["pages"])
app.include_router(organizations.router, prefix="/api", tags=["organizations"])
app.include_router(owner_explorer.router, prefix="/api", tags=["owner_explorer"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(drift.router, prefix="/api/drift", tags=["drift"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(auth_router, prefix="/api")
app.include_router(workflow.router, prefix="/api", tags=["workflow"])
app.include_router(sync_events.router, prefix="/api", tags=["sync_events"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
