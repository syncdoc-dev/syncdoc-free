"""Health check endpoints"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """Check API health status"""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "syncdoc-api",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/version")
async def version_info():
    """Get application version info"""
    settings = get_settings()
    return {
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    """Check database connectivity"""
    try:
        # Ensure connectivity and that core schema exists.
        await db.execute(text("SELECT 1"))
        await db.execute(text("SELECT 1 FROM users LIMIT 1"))
        return {"status": "healthy", "component": "database"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "component": "database", "error": str(e)},
        )
