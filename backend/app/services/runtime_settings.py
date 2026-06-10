"""Organization-aware runtime setting access."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import AppSetting


async def get_runtime_settings(
    db: AsyncSession,
    organization_id: str | None,
    keys: set[str] | None = None,
) -> dict[str, str]:
    """Return global legacy values overlaid with organization-specific values."""
    query = select(AppSetting).where(AppSetting.organization_id.is_(None))
    if organization_id is not None:
        query = select(AppSetting).where(
            or_(
                AppSetting.organization_id.is_(None),
                AppSetting.organization_id == organization_id,
            )
        )
    if keys:
        query = query.where(AppSetting.key.in_(keys))
    rows = (await db.execute(query)).scalars().all()

    values = {row.key: row.value for row in rows if row.organization_id is None}
    values.update({row.key: row.value for row in rows if row.organization_id == organization_id})
    return values


async def upsert_runtime_setting(
    db: AsyncSession,
    organization_id: str,
    key: str,
    value: str,
) -> None:
    result = await db.execute(
        select(AppSetting).where(
            AppSetting.organization_id == organization_id,
            AppSetting.key == key,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.value = value
    else:
        db.add(
            AppSetting(
                organization_id=organization_id,
                key=key,
                value=value,
            )
        )
