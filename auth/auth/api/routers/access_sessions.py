import fastapi as fs
import auth.api.schemas as sh

access_sessions_router = fs.APIRouter(prefix='/access_sessions')


@access_sessions_router.post('/access_sessions')
async def get_access_session(
    permission: list[sh.Permission]
) -> sh.Token:  # type: ignore
    pass


@access_sessions_router.get('/access_sessions/{id}')
async def access_session_data(
    id: int
) -> None:
    pass