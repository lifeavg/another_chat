from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DB_CONNECTION = 'postgresql+asyncpg'
DB_USER = 'postgres'
DB_PASSWORD = 'mysecretpassword'
DB_HOST = 'localhost:5432'
DB_NAME = 'test'


engine = create_async_engine(
    f'{DB_CONNECTION}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}',
    echo=True)


async def get_db_session() -> AsyncSession:  # type: ignore
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False)
    async with async_session() as session:  # type: ignore
        yield session
