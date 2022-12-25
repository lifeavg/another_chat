import fastapi as fs

from auth.api.routers.access_sessions import access_sessions_router
from auth.api.routers.login_sessions import login_sessions_router
from auth.api.routers.permissions import permissions_router
from auth.api.routers.services import services_router
from auth.api.routers.user_identification import user_identification_router
from auth.api.routers.users import users_router

app = fs.FastAPI()

app.include_router(access_sessions_router)
app.include_router(login_sessions_router)
app.include_router(permissions_router)
app.include_router(services_router)
app.include_router(user_identification_router)
app.include_router(users_router)