from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from .schemas import LoginAttemptResult
from .models import User, LoginAttempt

DB_CONNECTION = 'postgresql+asyncpg'
DB_USER = 'postgres'
DB_PASSWORD = 'mysecretpassword'
DB_HOST = 'localhost:5432'
DB_NAME = 'test'




engine = create_async_engine(f'{DB_CONNECTION}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}',
                             echo=True)

async def get_db_session() -> AsyncSession:  # type: ignore
    async_session = sessionmaker(engine,
                                 class_=AsyncSession,
                                 expire_on_commit=False)
    async with async_session() as session:  # type: ignore
        yield session


async def user_by_login(session: AsyncSession,
                           login: str,
                           active: bool | None = None
                           ) -> User:
    statement = ''
    if active is not None:
        statement = select(User).where(User.login == login,
                                       User.active == active)
    statement = select(User).where(User.login == login)
    return (await session.execute(statement)).scalars().first()

async def login_limit_by_fingerprint(session: AsyncSession,
                                     fingerprint: str,
                                     delay_minutes: int
                                     ) -> list[LoginAttempt]:
    statement = (select(LoginAttempt)
                 .where(LoginAttempt.fingerprint == fingerprint,
                        LoginAttempt.response.not_in((LoginAttemptResult.SUCCESS.value,
                                                      LoginAttemptResult.LIMIT_REACHED.value)),
                        (LoginAttempt.date_time ==
                         datetime.utcnow() - timedelta(minutes=delay_minutes)))
                 .order_by(LoginAttempt.date_time.desc()))
    return (await session.execute(statement)).scalars().all()
