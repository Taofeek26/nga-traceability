"""Read-only dashboard aggregation - ported from app.py's GET /."""
import db
import http_util as hu


def lambda_handler(event, context):
    lba_id = int(hu.claims(event)["lba_id"])
    with db.get_conn() as conn:
        n_farmers = conn.execute(
            "SELECT COUNT(*) c FROM farmers WHERE lba_id=%s", (lba_id,)
        ).fetchone()["c"]
        n_active = conn.execute(
            "SELECT COUNT(*) c FROM farmers WHERE lba_id=%s AND active=TRUE", (lba_id,)
        ).fetchone()["c"]
        potential = conn.execute(
            "SELECT COALESCE(SUM(potential_volume_kg),0) p FROM farmers WHERE lba_id=%s", (lba_id,)
        ).fetchone()["p"]
        delivered = conn.execute(
            """SELECT COALESCE(SUM(a.allocated_volume_kg),0) d FROM lot_allocations a
               JOIN farmers f ON f.id = a.farmer_id JOIN lots l ON l.id = a.lot_id
               WHERE f.lba_id=%s AND l.status = 'accepted'""",
            (lba_id,),
        ).fetchone()["d"]
        pending = conn.execute(
            """SELECT COALESCE(SUM(a.allocated_volume_kg),0) d FROM lot_allocations a
               JOIN farmers f ON f.id = a.farmer_id JOIN lots l ON l.id = a.lot_id
               WHERE f.lba_id=%s AND l.status = 'pending'""",
            (lba_id,),
        ).fetchone()["d"]
        n_lots = conn.execute(
            "SELECT COUNT(*) c FROM lots WHERE lba_id=%s", (lba_id,)
        ).fetchone()["c"]
        n_pending_lots = conn.execute(
            "SELECT COUNT(*) c FROM lots WHERE lba_id=%s AND status='pending'", (lba_id,)
        ).fetchone()["c"]
        recent_lots = conn.execute(
            """SELECT l.*, ROW_NUMBER() OVER (PARTITION BY l.lba_id ORDER BY l.id) AS lot_no
               FROM lots l WHERE l.lba_id=%s ORDER BY l.id DESC LIMIT 8""",
            (lba_id,),
        ).fetchall()
        near_limit = conn.execute(
            """
            SELECT f.farmer_code, f.full_name, f.potential_volume_kg,
                   COALESCE(SUM(a.allocated_volume_kg) FILTER (WHERE l.status = 'accepted'), 0) AS delivered
            FROM farmers f
            LEFT JOIN lot_allocations a ON a.farmer_id = f.id
            LEFT JOIN lots l ON l.id = a.lot_id
            WHERE f.lba_id=%s AND f.active = TRUE AND f.potential_volume_kg > 0
            GROUP BY f.id, f.farmer_code, f.full_name, f.potential_volume_kg
            HAVING COALESCE(SUM(a.allocated_volume_kg) FILTER (WHERE l.status = 'accepted'), 0) >= 0.9 * f.potential_volume_kg
            ORDER BY (COALESCE(SUM(a.allocated_volume_kg) FILTER (WHERE l.status = 'accepted'), 0) / f.potential_volume_kg) DESC
            LIMIT 10
            """,
            (lba_id,),
        ).fetchall()

    return hu.ok({
        "n_farmers": n_farmers,
        "n_active": n_active,
        "potential": potential,
        "delivered": delivered,
        "pending": pending,
        "n_lots": n_lots,
        "n_pending_lots": n_pending_lots,
        "recent_lots": recent_lots,
        "near_limit": near_limit,
    })
