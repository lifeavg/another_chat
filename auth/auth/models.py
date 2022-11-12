from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        MetaData, String, PrimaryKeyConstraint)
from sqlalchemy.orm import declarative_base, relationship


DB_SCHEMA = 'auth'

metadata_obj = MetaData(schema=DB_SCHEMA)
Base = declarative_base(metadata=metadata_obj)


class UserPermission(Base):
    __tablename__ = 'user_permission'
    __table_args__ = (PrimaryKeyConstraint('user_id', 'permission_id'),)
    user_id = Column(ForeignKey('user.id'), nullable=False)
    permission_id = Column(ForeignKey('permission.id'), nullable=False)
    given_at = Column(DateTime)
    permissions = relationship('Permission', back_populates='users')
    users = relationship('User', back_populates='permissions')


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, nullable=False)
    login = Column(String(32), nullable=False, unique=True)
    password = Column(String(128), nullable=False)
    active = Column(Boolean, nullable=False, default=False)
    permissions = relationship('UserPermission', back_populates='users')
    login_sessions = relationship('LoginSession', backref='users')
    login_attempts = relationship('LoginAttempt', backref='users')

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, external_id={self.external_id}, '
                f'login={self.login}, password={self.password})')


class LoginSession(Base):
    __tablename__ = 'login_session'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    stopped = Column(Boolean, nullable=False, default=False)
    access_sessions = relationship('AccessSession', backref='login_sessions')
    access_attempts = relationship('AccessAttempt', backref='login_sessions')

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, user_id={self.user_id}, '
                f'start={self.start}, end={self.end})')


class LoginAttempt(Base):
    __tablename__ = 'login_attempt'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    fingerprint = Column(String(256), nullable=False)
    date_time = Column(DateTime, nullable=False)
    response = Column(String(50), nullable=False)

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, user_id={self.user_id}, '
                f'fingerprint={self.fingerprint}, date_time={self.date_time}, '
                f'success={self.response})')


class AccessSession(Base):
    __tablename__ = 'access_session'
    id = Column(Integer, primary_key=True)
    login_session_id = Column(Integer, ForeignKey('login_session.id'), nullable=False)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    stopped = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, user_id={self.login_session_id}, '
                f'start={self.start}, end={self.end})')


class AccessAttempt(Base):
    __tablename__ = 'access_attempt'
    id = Column(Integer, primary_key=True)
    login_session_id = Column(Integer, ForeignKey('login_session.id'))
    fingerprint = Column(String(256), nullable=False)
    date_time = Column(DateTime, nullable=False)
    response = Column(String(50), nullable=False)

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, user_id={self.login_session_id}, '
                f'fingerprint={self.fingerprint}, date_time={self.date_time}, '
                f'success={self.response})')


class Service(Base):
    __tablename__ = 'service'
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    key = Column(String(256), nullable=False)
    permissions = relationship('Permission', backref='services')


class Permission(Base):
    __tablename__ = 'permission'
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    service_id = Column(Integer, ForeignKey('service.id'))
    users = relationship('UserPermission', back_populates='permissions')