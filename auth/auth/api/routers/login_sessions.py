import fastapi as fs

import auth.api.schemas as sh

login_sessions_router = fs.APIRouter(prefix='/login_sessions')


@login_sessions_router.get('/{id}')
async def login_session_data(
    id: int
) -> sh.LoginSession:  # type: ignore
    pass


@login_sessions_router.get('/{id}/access_sessions')
async def login_session_access_sessions(
    id: int,
    active: bool | None = None
) -> list[sh.AccessSession]:  # type: ignore
    pass


@login_sessions_router.post('/{id}/terminate')
async def terminate_login_session(
    id: int
) -> None:
    pass
