"""Public configuration endpoint"""

import json
import os

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
async def get_config() -> dict:
    """Return public runtime configuration for the frontend."""
    settings = get_settings()
    demo_creds = None
    if settings.demo_mode:
        creds_file = os.environ.get("DEMO_STATE_DIR", "/demo-state") + "/creds.json"
        if os.path.exists(creds_file):
            try:
                with open(creds_file) as f:
                    data = json.load(f)
                demo_creds = {
                    "username": data.get("username", settings.demo_username),
                    "password": data.get("password", settings.demo_password),
                    "reset_at": data.get("next_reset"),
                }
            except Exception:
                pass
        if demo_creds is None:
            demo_creds = {
                "username": settings.demo_username,
                "password": settings.demo_password,
                "reset_at": None,
            }
    stripe_config = {}
    if settings.billing_enabled:
        stripe_config = {
            "publishable_key": settings.effective_stripe_publishable_key,
            "pro_price_id": settings.stripe_pro_price_id,
            "team_price_id": settings.stripe_team_price_id,
            "test_mode": settings.billing_test_mode,
        }

    return {
        "demo_mode": settings.demo_mode,
        "demo_credentials": demo_creds,
        "self_registration_enabled": settings.allow_self_register,
        "stripe": stripe_config,
    }
