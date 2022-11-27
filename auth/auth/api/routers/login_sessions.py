import fastapi as fs

import auth.api.base as b
import auth.api.schemas as sh
import auth.db.connection as con
import auth.db.models as md
import auth.db.query as dq

login_sessions_router = fs.APIRouter(
    prefix='/login_sessions', tags=['login_sessions'])


@login_sessions_router.get('/{id}', response_model=sh.LoginSession)
async def login_session_data(
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> md.LoginSession:
    return await b.login_session_by_id(db_session, id)


@login_sessions_router.get('/{login_session_id}/access_sessions', response_model=list[sh.AccessSession])
async def login_session_access_sessions(
    login_session_id: int = fs.Path(ge=0),
    active: bool | None = None,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> list[md.AccessSession]:
    return await dq.login_session_access_sessions(db_session, login_session_id, active)
