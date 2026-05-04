import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import os


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def create_session_token(email: str) -> str:
    s = URLSafeTimedSerializer(os.environ["SECRET_KEY"])
    return s.dumps(email)


def decode_session_token(token: str) -> str | None:
    try:
        s = URLSafeTimedSerializer(os.environ["SECRET_KEY"])
        return s.loads(token, max_age=86400 * 7)
    except (BadSignature, SignatureExpired):
        return None
