import auth.db.connection as con
import auth.db.models as md
import auth.api.schemas as sh

from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import NoResultFound


async def user_by_login(
    session: con.AsyncSession,
    login: str,
    active: bool | None = None
) -> md.User | None:
    conditions = [(md.User.login == login), ]
    if active is not None:
        conditions.append((md.User.active == active))
    try:
        return (await session.execute(select(md.User).where(*conditions))).scalars().one()
    except NoResultFound:
        return None

async def user_by_id(
    session: AsyncSession,
    id: int,
    active: bool | None = None
) -> md.User | None:
    conditions = [(md.User.id == id), ]
    if active is not None:
        conditions.append((md.User.active == active))
    try:
        return (await session.execute(select(md.User).where(*conditions))).scalars().one()
    except NoResultFound:
        return None

async def user_with_permissions(
    session: AsyncSession,
    id: int,
    active: bool | None = None
) -> md.User | None:
    conditions = [(md.User.id == id), ]
    if active is not None:
        conditions.append((md.User.active == active))
    try:
        return (await session.execute(select(md.User)
                    .where(*conditions)
                    .options(selectinload(md.User.permissions))
                )).scalars().one()
    except NoResultFound:
        return None

async def user_permissions(
    session: AsyncSession,
    id: int
) -> list[sh.PermissionName]:
    statement = (select(md.Permission.name, md.User)
                 .join(md.User.permissions)
                 .where(md.User.id == id))
    return list((await session.execute(statement)).scalars().all())

async def permissions_by_names(
    session: AsyncSession,
    permissions: Iterable[sh.PermissionName]
) -> list[md.Permission]:
    statement = (select(md.Permission)
                 .where(md.Permission.name.in_(set(permissions))))
    return list((await session.execute(statement)).scalars().all())


async def login_limit_by_fingerprint(
    session: AsyncSession,
    fingerprint: str,
    delay_minutes: int
) -> list[md.LoginAttempt]:
    statement = (select(md.LoginAttempt)
                 .where(md.LoginAttempt.fingerprint == fingerprint,
                        md.LoginAttempt.response.not_in((
                            sh.LoginAttemptResult.SUCCESS.value,
                            sh.LoginAttemptResult.LIMIT_REACHED.value)),
                        (md.LoginAttempt.date_time ==
                         datetime.utcnow() - timedelta(minutes=delay_minutes)))
                 .order_by(md.LoginAttempt.date_time.desc()))
    return (await session.execute(statement)).scalars().all()
