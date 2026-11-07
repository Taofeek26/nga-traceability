"""Password hashing and signed-cookie sessions.

No server-side session store - the cookie itself carries the lba_id,
signed with SECRET_KEY so it can't be forged or edited client-side.
This is what lets auth work on Vercel's stateless serverless functions.
"""
import os

import bcrypt
from dotenv import load_dotenv
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Locally, put any random string in your .env file; "
        "on Vercel, add it as an environment variable before deploying."
    )

_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="lba-session")
COOKIE_NAME = "lba_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


ROLES = ("admin", "to", "lba")
ROLE_LABELS = {"admin": "Admin", "to": "Traceability Officer", "lba": "LBA"}


def make_session_token(user_id: int, lba_id: int, org_name: str, user_name: str, role: str) -> str:
    return _serializer.dumps({
        "user_id": user_id, "lba_id": lba_id,
        "org_name": org_name, "user_name": user_name, "role": role,
    })


def read_session_token(token: str):
    """Returns a dict with user_id/lba_id/org_name/user_name/role, or None
    if the cookie is missing/invalid/expired."""
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
        if "user_id" not in data or "lba_id" not in data:
            return None
        return data
    except (BadSignature, SignatureExpired):
        return None
