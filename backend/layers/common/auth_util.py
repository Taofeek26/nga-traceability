"""Password hashing and JWT session tokens.

Same bcrypt hashing as the original app's auth.py. The session itself
moves from a signed cookie to a signed JWT (same claim shape: user_id,
lba_id, org_name, user_name, role) because the frontend and backend are
now on different origins - see html/frontend-backend-split-plan.html §7.1.
"""
import json
import os
import time

import bcrypt
import boto3
import jwt

_secrets_client = boto3.client("secretsmanager")
_cached_jwt_secret = None

SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days, same as the cookie had

ROLES = ("admin", "to", "lba")
# The "lba" role's internal key is unchanged (no risky CHECK-constraint /
# existing-row migration) - only its display label changed, per request.
ROLE_LABELS = {"admin": "Admin", "to": "Traceability Officer", "lba": "Sourcing Manager"}


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


def _jwt_secret():
    global _cached_jwt_secret
    if _cached_jwt_secret:
        return _cached_jwt_secret
    secret_arn = os.environ["JWT_SECRET_ARN"]
    raw = _secrets_client.get_secret_value(SecretId=secret_arn)["SecretString"]
    try:
        _cached_jwt_secret = json.loads(raw)["jwtSigningKey"]
    except (json.JSONDecodeError, KeyError):
        _cached_jwt_secret = raw
    return _cached_jwt_secret


def make_session_token(user_id, lba_id, org_name, user_name, role, email=None):
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "lba_id": lba_id,
        "org_name": org_name,
        "user_name": user_name,
        "role": role,
        "email": email,
        "iat": now,
        "exp": now + SESSION_MAX_AGE_SECONDS,
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def read_session_token(token):
    try:
        data = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if "user_id" not in data or "lba_id" not in data:
        return None
    return data
