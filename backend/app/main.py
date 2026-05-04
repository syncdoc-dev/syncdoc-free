"""FastAPI application entry point"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin,
    analytics,
    api_keys,
    capabilities,
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
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    print("🚀 Starting SyncDoc API")
    await init_db()
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
