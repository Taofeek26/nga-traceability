"""Per-tenant settings - ported from app.py's /settings routes, plus
allocation_mode (added for the realistic-spread allocation option)."""
import db
import http_util as hu

ADMIN_ONLY = {"admin"}
ALLOCATION_MODES = {"full", "spread"}


def lambda_handler(event, context):
    deny = hu.require_role(event, ADMIN_ONLY)
    if deny:
        return deny

    lba_id = int(hu.claims(event)["lba_id"])
    if hu.method(event) == "GET":
        rate = db.get_setting(lba_id, "premium_rate_per_kg", "0")
        allocation_mode = db.get_setting(lba_id, "allocation_mode", "full")
        return hu.ok({"premium_rate_per_kg": rate, "allocation_mode": allocation_mode})

    body = hu.json_body(event)
    user_id = int(hu.claims(event)["user_id"])

    if "premium_rate_per_kg" in body:
        rate = body.get("premium_rate_per_kg")
        if rate is None:
            return hu.error(400, "premium_rate_per_kg is required.")
        db.set_setting(lba_id, "premium_rate_per_kg", str(rate))
        with db.get_conn() as conn:
            db.log_audit(conn, lba_id, user_id, "settings.updated", "setting",
                          "premium_rate_per_kg", str(rate))

    if "allocation_mode" in body:
        mode = body.get("allocation_mode")
        if mode not in ALLOCATION_MODES:
            return hu.error(400, "Invalid allocation_mode.")
        db.set_setting(lba_id, "allocation_mode", mode)
        with db.get_conn() as conn:
            db.log_audit(conn, lba_id, user_id, "settings.updated", "setting", "allocation_mode", mode)

    return hu.ok({"ok": True})
