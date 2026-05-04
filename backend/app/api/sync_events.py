"""WebSocket endpoint for real-time sync progress and drift alerts."""

from __future__ import annotations

import jwt as pyjwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.core.rbac import ensure_membership
from app.core.security import decode_access_token
from app.models.user import User
from app.services.sync_events import subscribe_sync_events

router = APIRouter()


async def _authenticate_websocket(websocket: WebSocket, db: AsyncSession) -> str | None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Missing token")
        return None

    try:
        payload = decode_access_token(token)
    except pyjwt.ExpiredSignatureError:
        await websocket.close(code=4401, reason="Token expired")
        return None
    except pyjwt.InvalidTokenError:
        await websocket.close(code=4401, reason="Invalid token")
        return None

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        await websocket.close(code=4401, reason="User not found")
        return None

    membership = await ensure_membership(db, user.id, create_if_missing=False)
    return membership.organization_id


@router.websocket("/ws/sync-events")
async def sync_events_websocket(websocket: WebSocket) -> None:
    await websocket.accept()

    async with get_session_factory()() as db:
        organization_id = await _authenticate_websocket(websocket, db)
        if not organization_id:
            return

    try:
        async for event in subscribe_sync_events(organization_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
