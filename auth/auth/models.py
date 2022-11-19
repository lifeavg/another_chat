from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        MetaData, PrimaryKeyConstraint, String, Table, func,
                        UniqueConstraint)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql.functions import GenericFunction

DB_SCHEMA = 'auth'

metadata_obj = MetaData(schema=DB_SCHEMA)
Base = declarative_base(metadata=metadata_obj)


class now_utc(GenericFunction):
    type = DateTime(timezone=True)
    inherit_cache = True


user_permission = Table(
    'user_permission',
    Base.metadata,
    Column('user_id', ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
    Column('permission_id', ForeignKey(
        'permission.id', ondelete='CASCADE'), nullable=False),
    PrimaryKeyConstraint('user_id', 'permission_id')
)


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, nullable=False)
    login = Column(String(32), nullable=False, unique=True)
    password = Column(String(128), nullable=False)
    confirmed = Column(Boolean, nullable=False, default=False)
    active = Column(Boolean, nullable=False, default=True)
    created_timestamp = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now_utc())
    permissions = relationship(
        'Permission', secondary=user_permission, backref="users")
    login_sessions = relationship('LoginSession', backref='users')
    login_attempts = relationship('LoginAttempt', backref='users')

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, external_id={self.external_id}, '
                f'login={self.login}, password={self.password}, '
                f'created_timestamp={self.created_timestamp})')


class LoginSession(Base):
    __tablename__ = 'login_session'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(
        'user.id', ondelete='CASCADE'), nullable=False)
    start = Column(DateTime(timezone=True), nullable=False)
    end = Column(DateTime(timezone=True), nullable=False)
    stopped = Column(Boolean, nullable=False, default=False)
    access_sessions = relationship('AccessSession', backref='login_sessions')
    access_attempts = relationship('AccessAttempt', backref='login_sessions')

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, user_id={self.user_id}, '
                f'start={self.start}, end={self.end})')


class LoginAttempt(Base):
    __tablename__ = 'login_attempt'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(
        'user.id', ondelete='CASCADE'), nullable=True)
    fingerprint = Column(String(256), nullable=False)
    date_time = Column(DateTime(timezone=True), nullable=False)
    response = Column(String(50), nullable=False)

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, user_id={self.user_id}, '
                f'fingerprint={self.fingerprint}, date_time={self.date_time}, '
                f'success={self.response})')


class AccessSession(Base):
    __tablename__ = 'access_session'
    id = Column(Integer, primary_key=True)
    login_session_id = Column(Integer, ForeignKey(
        'login_session.id', ondelete='CASCADE'), nullable=False)
    start = Column(DateTime(timezone=True), nullable=False)
    end = Column(DateTime(timezone=True), nullable=False)
    stopped = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, user_id={self.login_session_id}, '
                f'start={self.start}, end={self.end})')


class AccessAttempt(Base):
    __tablename__ = 'access_attempt'
    id = Column(Integer, primary_key=True)
    login_session_id = Column(Integer, ForeignKey(
        'login_session.id', ondelete='CASCADE'), nullable=True)
    fingerprint = Column(String(256), nullable=False)
    date_time = Column(DateTime(timezone=True), nullable=False)
    response = Column(String(50), nullable=False)

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, user_id={self.login_session_id}, '
                f'fingerprint={self.fingerprint}, date_time={self.date_time}, '
                f'success={self.response})')


class Service(Base):
    __tablename__ = 'service'
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False, unique=True)
    key = Column(String(256), nullable=False)
    permissions = relationship('Permission', back_populates="service")

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, name={self.name}, '
                f'key={self.key})')


class Permission(Base):
    __tablename__ = 'permission'
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False, unique=True)
    service_id = Column(Integer, ForeignKey(
        'service.id', ondelete='CASCADE'), nullable=False)
    service = relationship('Service', back_populates="permissions")

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, name={self.name}, '
                f'service_id={self.service_id})')
