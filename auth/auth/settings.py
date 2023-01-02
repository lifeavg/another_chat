from pydantic import BaseSettings


class _SettingsSQL(BaseSettings):
    user_: str = 'postgres'
    password: str = 'mysecretpassword'
    host: str = 'localhost:5432'
    name: str = 'test'


class _SettingsSecurity(BaseSettings):
    # minutes
    session_expire: int = 300
    attempt_delay: int = 5
    max_attempt_count: int = 5
    algorithm: str = 'HS256'
    session_key: bytes = b'1234567890'
    access_key: bytes = b'4321qwerty'
    password_hash_schemas: list[str] = ['bcrypt']


class _Settings(BaseSettings):
    sql: _SettingsSQL = _SettingsSQL()
    security: _SettingsSecurity = _SettingsSecurity()


settings = _Settings()
