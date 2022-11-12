import asyncio

from ..auth.db import get_db_session
from ..auth.models import (AccessAttempt, LoginAttempt, LoginSession,
                           Permission, Service, User, UserPermission)


async def main():
    async for session in get_db_session():  # type: ignore
        u = User(external_id = 11, 
                login = 'userlogin', 
                password = 'userpassword', 
                active = True)
        session.add(u)
        await session.commit()
        break

asyncio.run(main())


