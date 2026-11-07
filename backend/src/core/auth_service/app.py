"""Signup, login, logout - ported from app.py's /signup, /login, /logout.

Same bcrypt hashing and the same lbas/users inserts as the original app;
the only change is a JWT returned in the response body instead of a
Set-Cookie header (see html/frontend-backend-split-plan.html §7.1).
"""
import psycopg2.errors

import auth_util
import db
import http_util as hu


def lambda_handler(event, context):
    path = event["rawPath"]
    if path.endswith("/signup"):
        return _signup(event)
    if path.endswith("/login"):
        return _login(event)
    if path.endswith("/logout"):
        return hu.ok({"ok": True})
    return hu.error(404, "Not found")


def _signup(event):
    body = hu.json_body(event)
    name = (body.get("name") or "").strip()
    email_norm = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    confirm_password = body.get("confirm_password") or ""

    if not name or not email_norm:
        return hu.error(400, "Name and email are required.")
    if password != confirm_password:
        return hu.error(400, "Passwords do not match.")
    if len(password) < 8:
        return hu.error(400, "Password must be at least 8 characters.")

    try:
        with db.get_conn() as conn:
            existing = conn.execute("SELECT 1 FROM users WHERE email=%s", (email_norm,)).fetchone()
            if existing:
                return hu.error(409, "An account with that email already exists.")
            lba_row = conn.execute(
                "INSERT INTO lbas (name) VALUES (%s) RETURNING id", (name,)
            ).fetchone()
            lba_id = lba_row["id"]
            user_row = conn.execute(
                "INSERT INTO users (lba_id, name, email, password_hash, role) "
                "VALUES (%s,%s,%s,%s,'admin') RETURNING id",
                (lba_id, name, email_norm, auth_util.hash_password(password)),
            ).fetchone()
            user_id = user_row["id"]
    except psycopg2.errors.UniqueViolation:
        return hu.error(409, "An account with that email already exists.")

    token = auth_util.make_session_token(user_id, lba_id, name, name, "admin", email_norm)
    return hu.created({"token": token, "user": {
        "user_id": user_id, "lba_id": lba_id, "org_name": name, "user_name": name, "role": "admin",
        "email": email_norm,
    }})


def _login(event):
    body = hu.json_body(event)
    email_norm = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    with db.get_conn() as conn:
        row = conn.execute(
            """SELECT u.*, l.name AS org_name FROM users u
               JOIN lbas l ON l.id = u.lba_id
               WHERE u.email=%s""",
            (email_norm,),
        ).fetchone()

    if not row or not row["active"] or not auth_util.verify_password(password, row["password_hash"]):
        return hu.error(401, "Invalid email or password.")

    token = auth_util.make_session_token(
        row["id"], row["lba_id"], row["org_name"], row["name"], row["role"], row["email"]
    )
    return hu.ok({"token": token, "user": {
        "user_id": row["id"], "lba_id": row["lba_id"], "org_name": row["org_name"],
        "user_name": row["name"], "role": row["role"], "email": row["email"],
    }})
