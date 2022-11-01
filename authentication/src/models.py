from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        MetaData, String)
from sqlalchemy.orm import declarative_base, relationship


DB_SCHEMA = 'authentication'

metadata_obj = MetaData(schema=DB_SCHEMA)
Base = declarative_base(metadata=metadata_obj)


class LoginData(Base):
    __tablename__ = 'login_data'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    login = Column(String(32), nullable=False, unique=True)
    password = Column(String(128), nullable=False)
    active = Column(Boolean, nullable=False, default=False)
    sessions = relationship('LoginSession')

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, user_id={self.user_id}, '
                f'login={self.login}, password={self.password})')


class LoginSession(Base):
    __tablename__ = 'login_session'
    id = Column(Integer, primary_key=True)
    login_data_id = Column(Integer, ForeignKey(
        'login_data.id'), nullable=False)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    stopped = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, login_data_id={self.login_data_id}, '
                f'start={self.start}, end={self.end})')


class LoginAttempt(Base):
    __tablename__ = 'login_attempt'
    id = Column(Integer, primary_key=True)
    login_data_id = Column(Integer, ForeignKey('login_data.id'))
    fingerprint = Column(String(256), nullable=False)
    date_time = Column(DateTime, nullable=False)
    response = Column(String(50), nullable=False)
    login_data = relationship('LoginData')

    def __repr__(self) -> str:
        return (f'{self.__class__}(id={self.id}, login_data_id={self.login_data_id}, '
                f'fingerprint={self.fingerprint}, date_time={self.date_time}, '
                f'success={self.response})')