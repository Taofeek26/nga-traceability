"""Login, logout - ported from app.py's /login, /logout.

No signup: this stack is provisioned for one LBA. Onboarding another LBA
means standing up another stack (see infra/resource-mapping/), not
self-registering a second tenant inside this one - so there's no public
endpoint that can INSERT a new row into lbas.
"""
import auth_util
import db
import http_util as hu


def lambda_handler(event, context):
    path = event["rawPath"]
    if path.endswith("/login"):
        return _login(event)
    if path.endswith("/logout"):
        return hu.ok({"ok": True})
    return hu.error(404, "Not found")


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
