from datetime import datetime, timedelta, timezone

import pytest

from auth.api.schemas import AccessTokenData, SessionTokenData
from auth.security import SEC_SECRET_ACCESS, SEC_SECRET_SESSION, create_token

HOST: str = 'http://localhost:8080'


@pytest.fixture
def authorization(perms: list[str]) -> dict[str, str]:
    token_exp = datetime.now(timezone.utc) + timedelta(days=2)
    access_data = AccessTokenData(jti=1, sub=1, pms=perms, exp=token_exp)
    return {'Authorization': 'Bearer ' +
            create_token(access_data.dict(), SEC_SECRET_ACCESS)}


@pytest.fixture
def session() -> dict[str, str]:
    token_exp = datetime.now(timezone.utc) + timedelta(days=2)
    session_data = SessionTokenData(jti=1, sub=1, exp=token_exp)
    return {'Authorization': 'Bearer ' +
            create_token(session_data.dict(), SEC_SECRET_SESSION)}
