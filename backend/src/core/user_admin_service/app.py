"""Staff account management - ported from app.py's /users routes."""
import psycopg2.errors

import auth_util
import db
import http_util as hu

ADMIN_ONLY = {"admin"}


def lambda_handler(event, context):
    m = hu.method(event)
    path = event["rawPath"]

    forbidden = hu.require_role(event, ADMIN_ONLY)
    if forbidden:
        return forbidden

    lba_id = int(hu.claims(event)["lba_id"])

    if path.endswith("/toggle-active"):
        return _toggle_active(event, lba_id)
    if m == "GET":
        return _list(lba_id)
    if m == "POST":
        return _create(event, lba_id)
    return hu.error(404, "Not found")


def _list(lba_id):
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT id, lba_id, name, email, role, active, created_at FROM users "
            "WHERE lba_id=%s ORDER BY role, name",
            (lba_id,),
        ).fetchall()
    return hu.ok({"team": rows, "roles": list(auth_util.ROLES), "role_labels": auth_util.ROLE_LABELS})


def _create(event, lba_id):
    body = hu.json_body(event)
    name = (body.get("name") or "").strip()
    email_norm = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    role = body.get("role") or ""

    if role not in auth_util.ROLES:
        return hu.error(400, "Invalid role.")
    if len(password) < 8:
        return hu.error(400, "Password must be at least 8 characters.")

    try:
        with db.get_conn() as conn:
            existing = conn.execute("SELECT 1 FROM users WHERE email=%s", (email_norm,)).fetchone()
            if existing:
                return hu.error(409, "That email is already in use.")
            conn.execute(
                "INSERT INTO users (lba_id, name, email, password_hash, role) VALUES (%s,%s,%s,%s,%s)",
                (lba_id, name, email_norm, auth_util.hash_password(password), role),
            )
            db.log_audit(conn, lba_id, int(hu.claims(event)["user_id"]), "user.created", "user", email_norm,
                          auth_util.ROLE_LABELS[role])
    except psycopg2.errors.UniqueViolation:
        return hu.error(409, "That email is already in use.")
    return hu.created({"name": name, "role": role, "role_label": auth_util.ROLE_LABELS[role]})


def _toggle_active(event, lba_id):
    user_id = int(hu.path_params(event)["id"])
    caller_id = int(hu.claims(event)["user_id"])
    if user_id == caller_id:
        return hu.error(400, "You can't deactivate your own account.")
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET active = NOT active WHERE id=%s AND lba_id=%s",
            (user_id, lba_id),
        )
        db.log_audit(conn, lba_id, caller_id, "user.toggled_active", "user", user_id, None)
    return hu.ok({"ok": True})
