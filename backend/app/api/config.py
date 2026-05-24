"""Public configuration endpoint"""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
async def get_config() -> dict:
    """Return public runtime configuration for the frontend."""
    settings = get_settings()
    return {
        "demo_mode": settings.demo_mode,
        "demo_credentials": (
            {"username": settings.demo_username, "password": settings.demo_password}
            if settings.demo_mode
            else None
        ),
    }
