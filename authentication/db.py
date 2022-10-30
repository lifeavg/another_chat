from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from schemas import LoginAttemptResult
from models import LoginData, LoginAttempt

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


async def get_login_data_by_login(session: AsyncSession, login: str, active: bool | None = None) -> LoginData:
    statement = ''
    if active is not None:
        statement = select(LoginData).where(LoginData.login == login,
                                            LoginData.active == active)
    statement = select(LoginData).where(LoginData.login == login)
    return (await session.execute(statement)).scalars().first()

async def get_login_limit_by_fingerprint(session: AsyncSession, fingerprint: str, delay_minutes: int) -> list[LoginAttempt]:
    statement = (select(LoginAttempt)
                 .where(LoginAttempt.fingerprint == fingerprint,
                        LoginAttempt.response.not_in((LoginAttemptResult.SUCCESS.value, LoginAttemptResult.LIMIT_REACHED.value)),
                        LoginAttempt.date_time == datetime.utcnow() - timedelta(minutes=delay_minutes))
                 .order_by(LoginAttempt.date_time.desc()))
    return (await session.execute(statement)).scalars().all()
