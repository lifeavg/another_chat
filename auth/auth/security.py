from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

import auth.db.query as dq


SEC_ACCESS_EXPIRE_MINUTES = 30
SEC_ATTEMPT_DELAY_MINUTES = 10
SEC_MAX_ATTEMPT_DELAY_COUNT = 5

SEC_ALGORITHM = 'RS512'
SEC_PUB = b'-----BEGIN PUBLIC KEY-----\nMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA0VDAbHpYVGILHOwQ6pMhA6VRvhRJalm81TOrULntvB63CaovsYQfZy4p7r7fjeKtXSxs3p4ZTrS6d9KS9aHvL37KoijsJ79aiSZAgLSLMBr4bLNJAqkTw9GLUxy4KaeMQNXN9TtCxkiSSDOO/1a4/OdPR+Kd9wukW6pzagIRE29HB76FaD8peCNswm5mT0lYJq5uUHVsHkhRqdfI6P3k7Lm+MckDaaEN8IbLvI+UboI4P82OdM9k8Qv0o0JOay6EKGVsjj/y5Fl3R8YAkt4GenZkMrkDAH3xUTOOykWIz/Z+n+e9qj0ZJuiqsrFF2nlC9EhfTnnKS2X9GVSLt57+poTLm2f0M1ohv9QJLINRjAzKnaR4YG6fR9E4jNLx3iZ8bdyxWjBLe/PXmGG0DomYIHGjRI/79ZZjk1sNASpiJLXswrThWXd3jYbJSuOExJTfivYwUeL15dmfkZoPoluwKY+6kvPUG7+A4YEkGpVbuEC1l+QTkHHfRJbg9IgluzzicwLRORDST+kC+rG1bTXP91Ug0CCEBvr1agFIWuMnDKGlxsQPofDZWsjM6M7mH71ZcbbkcYXFHsJpKi8Z2tqTre1pVe3WXzK73QAMtAThYyXNjFPOgvANeCIqk41S28k9z+6X7SaXfW9hpWnZGesoUoo/9J6MV/iPdid4gHOuM50CAwEAAQ==\n-----END PUBLIC KEY-----'
SEC_PRI = b'-----BEGIN PRIVATE KEY-----\n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\n-----END PRIVATE KEY-----'


pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict,
                        secret: bytes = SEC_PUB,
                        algorithm: str = SEC_ALGORITHM
                        ) -> str:
    encoded_jwt = jwt.encode(data, secret, algorithm)
    return encoded_jwt

async def login_limit(session: dq.AsyncSession,
                      fingerprint: str,
                      delay_minutes: int = SEC_ATTEMPT_DELAY_MINUTES,
                      max_attempts: int = SEC_MAX_ATTEMPT_DELAY_COUNT) -> timedelta | None:
    attempts = await dq.login_limit_by_fingerprint(session, fingerprint, delay_minutes)
    if len(attempts) >= max_attempts:
        return timedelta(minutes=delay_minutes) - (datetime.utcnow() - attempts[0].date_time())

def new_password_validator(password: str) -> tuple[bool, str]:
    # TODO
    return True, 'OK'
