from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import auth.api.schemas as sh
import auth.db.connection as con
import auth.db.models as md


async def user_by_login(
    session: con.AsyncSession,
    login: str,
    active: bool | None = None
) -> md.User | None:
    conditions = [(md.User.login == login), ]
    if active is not None:
        conditions.append((md.User.active == active))
    try:
        return (await session.execute(select(md.User).where(*conditions))
                ).scalars().one()
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
        return (await session.execute(select(md.User).where(*conditions))
                ).scalars().one()
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
                                      )
                ).scalars().one()
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


async def user_login_sessions(
    session: con.AsyncSession,
    id: int,
    limit: int,
    offset: int,
    active: bool | None = None
) -> list[md.LoginSession]:
    conditions = [(md.LoginSession.user_id == id), ]
    match active:
        case True:
            conditions.append((md.LoginSession.stopped == (not active)))
            conditions.append((md.LoginSession.end > func.now_utc()))
        case False:
            conditions.append(
                or_(md.LoginSession.stopped == (not active),
                    md.LoginSession.end > func.now_utc())
            )
        case _:
            pass
    return (await session.execute(select(md.LoginSession)
                                  .where(*conditions)
                                  .order_by(md.LoginSession.start.desc())
                                  .limit(limit)
                                  .offset(offset))
            ).scalars().all()


async def delete_user(
    session: con.AsyncSession,
    id: int
) -> int | None:
    try:
        return (await session.execute(delete(md.User)
                                      .where(md.User.id == id)
                                      .returning(md.User.id))
                ).scalars().one()
    except NoResultFound:
        return None


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
