import sys
from datetime import datetime, timedelta, timezone

import httpx

from auth.api.schemas import AccessTokenData, Login, Permission, Service, User
from auth.security import TOKEN_NAME, create_token
from auth.settings import settings

PERMISSIONS = [
    Permission(name='auth_del_user', expiration_min=2),
    Permission(name='auth_upd_user', expiration_min=2),
    Permission(name='auth_adm', expiration_min=10),
    Permission(name='auth_mod', expiration_min=20)
]


if len(sys.argv) < 3:
    sys.exit('Usage: python initial_setup.py host admin_user_password')
host = sys.argv[1]
password = sys.argv[2]


new_user_data = Login(login='admin', password=password)
new_user_response = httpx.post(url=f'{host}/signup', json=new_user_data.dict())
if new_user_response.status_code != 201:
    sys.exit(f'Error on creating new user: {new_user_data}\n \
      {new_user_response.status_code}\n{new_user_response.text}')
new_user = User(**new_user_response.json())


token = create_token(
    data=AccessTokenData(
        jti=1,
        sub=new_user.id, pms=['auth_upd_user', 'auth_adm'],
        exp=datetime.now(timezone.utc) + timedelta(minutes=10)).dict(),
    secret=settings.security.access_key,
    algorithm=settings.security.algorithm)
headers = {'Authorization': ' '.join((TOKEN_NAME, token))}


confirm_user_response = httpx.put(
    url=f'{host}/users/{new_user.id}?confirmed=True', headers=headers)
if confirm_user_response.status_code != 200:
    sys.exit(f'Error on confirming user: {confirm_user_response.status_code}\n \
      {confirm_user_response.text}')


auth_service = Service(name='auth', key=settings.security.access_key.decode('utf-8'))
create_service_response = httpx.post(
    url=f'{host}/services/', json=auth_service.dict(), headers=headers)
if create_service_response.status_code != 201:
    sys.exit(f'Error on creating service: {create_service_response.status_code}\n \
      {create_service_response.text}')


for permission in PERMISSIONS:
    create_permission_response = httpx.post(
        url=f'{host}/services/{auth_service.name}/permissions',
        json=permission.dict(), headers=headers)
    if create_permission_response.status_code != 200:
        sys.exit(f'Error on creating permission {permission}\n \
          {create_permission_response.status_code}\n{create_permission_response.text}')


add_permissions_response = httpx.post(
    url=f'{host}/users/{new_user.id}/permissions/add',
    json=[p.name for p in PERMISSIONS],
    headers=headers)
if add_permissions_response.status_code != 200:
    sys.exit(f'Error on adding permissions: {add_permissions_response.status_code}\n \
      {add_permissions_response.text}')
