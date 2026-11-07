"""Read-only audit trail: who did what, when. Admin-only - see
db.log_audit() call sites across the other services for what gets recorded."""
import db
import http_util as hu

ADMIN_ONLY = {"admin"}


def lambda_handler(event, context):
    deny = hu.require_role(event, ADMIN_ONLY)
    if deny:
        return deny
    lba_id = int(hu.claims(event)["lba_id"])

    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT a.id, a.action, a.entity_type, a.entity_id, a.details, a.created_at,
                   u.name AS actor_name
            FROM audit_log a
            LEFT JOIN users u ON u.id = a.user_id
            WHERE a.lba_id = %s
            ORDER BY a.created_at DESC
            LIMIT 200
            """,
            (lba_id,),
        ).fetchall()

    return hu.ok({"entries": rows})
