from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from auth.settings import settings

DB_CONNECTION = 'postgresql+asyncpg'


engine = create_async_engine(
    (f'{DB_CONNECTION}://{settings.sql.user_}:'
     f'{settings.sql.password}@{settings.sql.host}'
     f'/{settings.sql.name}'),
    echo=True)


async def get_db_session() -> AsyncSession:  # type: ignore
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False)
    async with async_session() as session:  # type: ignore
        yield session
