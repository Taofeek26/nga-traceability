"""Lot lifecycle - ported from app.py's /lots routes.

allocate_lot's proportional-split algorithm, the per-farmer bag floor of 1
(derived from weight at 62.5kg/bag), and the per-farmer delivered_date
randomization are all carried over unchanged from the original app.
"""
import io
import os
import random as _random
from datetime import date, timedelta

import boto3
import openpyxl

import db
import http_util as hu
from allocation import allocate_lot, AllocationError

STANDARD_BAG_KG = 62.5
ROLES_CAN_CREATE_LOT = {"admin", "to"}
ROLES_CAN_REVIEW_LOT = {"admin", "lba"}

_s3 = boto3.client("s3")
EXPORTS_BUCKET = os.environ.get("EXPORTS_BUCKET")


def lambda_handler(event, context):
    m = hu.method(event)
    path = event["rawPath"]
    lba_id = int(hu.claims(event)["lba_id"])

    if path.endswith("/eligibility"):
        return _eligibility(lba_id)
    if path.endswith("/accept"):
        return _review(event, lba_id, "accepted")
    if path.endswith("/reject"):
        return _review(event, lba_id, "rejected")
    if path.endswith("/export"):
        return _export(event, lba_id)
    if path.endswith("/receipts"):
        return _receipts(event, lba_id)
    if m == "GET" and hu.path_params(event).get("id"):
        return _detail(event, lba_id)
    if m == "GET":
        return _list(lba_id)
    if m == "POST":
        return _create(event, lba_id)
    return hu.error(404, "Not found")


def _eligible_farmers(conn, lba_id):
    """A farmer's remaining quota counts only *accepted* deliveries - a
    pending lot doesn't reserve anything. That means two different pending
    lots can each be built against a farmer's full remaining quota; the
    accept-time check in _review() is what actually stops a farmer from
    ever ending up over-delivered once both get accepted."""
    # potential - opening_delivered_kg (whatever this farmer already had
    # delivered before being tracked here, from a manually-managed
    # register uploaded at onboarding) - accepted lot volume.
    return conn.execute(
        """
        SELECT f.id,
               f.potential_volume_kg - f.opening_delivered_kg - COALESCE(SUM(a.allocated_volume_kg)
                   FILTER (WHERE l.status = 'accepted'), 0) AS remaining
        FROM farmers f
        LEFT JOIN lot_allocations a ON a.farmer_id = f.id
        LEFT JOIN lots l ON l.id = a.lot_id
        WHERE f.lba_id=%s AND f.active = TRUE
        GROUP BY f.id
        HAVING f.potential_volume_kg - f.opening_delivered_kg - COALESCE(SUM(a.allocated_volume_kg)
            FILTER (WHERE l.status = 'accepted'), 0) > 0
        """,
        (lba_id,),
    ).fetchall()


def _eligibility(lba_id):
    with db.get_conn() as conn:
        n_eligible = len(_eligible_farmers(conn, lba_id))
    return hu.ok({"n_eligible": n_eligible, "standard_bag_kg": STANDARD_BAG_KG})


def _list(lba_id):
    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT l.*, COUNT(a.id) n_farmers,
                   ROW_NUMBER() OVER (PARTITION BY l.lba_id ORDER BY l.id) AS lot_no
            FROM lots l LEFT JOIN lot_allocations a ON a.lot_id = l.id
            WHERE l.lba_id=%s
            GROUP BY l.id ORDER BY l.id DESC
            """,
            (lba_id,),
        ).fetchall()
    return hu.ok({"lots": rows})


def _create(event, lba_id):
    deny = hu.require_role(event, ROLES_CAN_CREATE_LOT)
    if deny:
        return deny
    body = hu.json_body(event)

    try:
        lot_date_obj = date.fromisoformat(body.get("lot_date", ""))
        if lot_date_obj > date.today():
            return hu.error(400, "Delivery date can't be later than today.")
    except ValueError:
        return hu.error(400, "Invalid delivery date.")

    try:
        total_volume_kg = float(body["total_volume_kg"])
        receipt_start = int(body["receipt_start"])
        receipt_end = int(body["receipt_end"])
    except (KeyError, ValueError, TypeError):
        return hu.error(400, "total_volume_kg, receipt_start, and receipt_end are required.")
    if receipt_end < receipt_start:
        return hu.error(400, "Receipt end number must be greater than or equal to the start number.")

    note = (body.get("note") or "").strip()
    vehicle_plate = (body.get("vehicle_plate") or "").strip()
    driver_name = (body.get("driver_name") or "").strip()
    waybill_number = (body.get("waybill_number") or "").strip()
    moisture_pct = body.get("moisture_pct")
    moisture_val = float(moisture_pct) if moisture_pct not in (None, "") else None

    n_receipts = receipt_end - receipt_start + 1
    preferred_codes = [c.strip() for c in (body.get("preferred_farmer_codes") or []) if c and c.strip()]

    with db.get_conn() as conn:
        rows = _eligible_farmers(conn, lba_id)
        eligible = [(r["id"], r["remaining"]) for r in rows]

        required_ids = set()
        if preferred_codes:
            eligible_by_id = {r["id"] for r in rows}
            resolved = conn.execute(
                "SELECT id, farmer_code FROM farmers WHERE lba_id=%s AND farmer_code = ANY(%s)",
                (lba_id, preferred_codes),
            ).fetchall()
            required_ids = {r["id"] for r in resolved if r["id"] in eligible_by_id}
            # Silently drop any preferred farmer that isn't currently
            # eligible (inactive, no remaining quota, or not found) rather
            # than failing the whole lot over a stale preference.

        allocation_mode = db.get_setting(lba_id, "allocation_mode", "full")

        try:
            allocation = allocate_lot(
                eligible, total_volume_kg, n_receipts,
                required_ids=required_ids, spread_mode=(allocation_mode == "spread"),
            )
        except AllocationError as e:
            return hu.error(400, str(e))

        bag_split = {
            fid: max(1, round(vol / STANDARD_BAG_KG)) for fid, vol in allocation.items() if vol > 0
        }
        bags_declared_val = sum(bag_split.values())

        lot_row = conn.execute(
            """INSERT INTO lots (lba_id, lot_date, total_volume_kg, receipt_start, receipt_end, note,
               vehicle_plate, driver_name, waybill_number, bags_declared, moisture_pct, status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending') RETURNING id""",
            (lba_id, body["lot_date"], total_volume_kg, receipt_start, receipt_end, note,
             vehicle_plate or None, driver_name or None, waybill_number or None,
             bags_declared_val, moisture_val),
        )
        lot_id = lot_row.fetchone()["id"]

        receipt_numbers = list(range(receipt_start, receipt_end + 1))
        farmer_ids = list(allocation.keys())
        _random.shuffle(farmer_ids)
        for receipt_no, farmer_id in zip(receipt_numbers, farmer_ids):
            farmer_delivered_date = (lot_date_obj - timedelta(days=_random.randint(0, 6))).isoformat()
            conn.execute(
                "INSERT INTO lot_allocations "
                "(lot_id, farmer_id, receipt_number, allocated_volume_kg, num_bags, delivered_date) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (lot_id, farmer_id, receipt_no, allocation[farmer_id], bag_split.get(farmer_id),
                 farmer_delivered_date),
            )

        db.log_audit(conn, lba_id, int(hu.claims(event)["user_id"]), "lot.created", "lot", lot_id,
                      f"{total_volume_kg:g}kg across {n_receipts} receipt(s)")

    return hu.created({"lot_id": lot_id})


def _detail(event, lba_id):
    lot_id = int(hu.path_params(event)["id"])
    with db.get_conn() as conn:
        lot = conn.execute(
            """SELECT l.*, (SELECT COUNT(*) FROM lots l2 WHERE l2.lba_id=l.lba_id AND l2.id<=l.id) AS lot_no
               FROM lots l WHERE l.id=%s AND l.lba_id=%s""",
            (lot_id, lba_id),
        ).fetchone()
        if not lot:
            return hu.error(404, "Lot not found.")
        rows = conn.execute(
            """
            SELECT a.receipt_number, a.allocated_volume_kg, a.num_bags, a.gross_weight_kg,
                   COALESCE(a.delivered_date, l.lot_date) AS delivered_date,
                   f.farmer_code, f.full_name, f.community, f.farmer_uid
            FROM lot_allocations a
            JOIN farmers f ON f.id = a.farmer_id
            JOIN lots l ON l.id = a.lot_id
            WHERE a.lot_id = %s ORDER BY a.receipt_number
            """,
            (lot_id,),
        ).fetchall()
        reviewer = None
        if lot["reviewed_by"]:
            r = conn.execute("SELECT name FROM users WHERE id=%s", (lot["reviewed_by"],)).fetchone()
            reviewer = r["name"] if r else None
    return hu.ok({"lot": lot, "rows": rows, "reviewer": reviewer})


def _review(event, lba_id, new_status):
    deny = hu.require_role(event, ROLES_CAN_REVIEW_LOT)
    if deny:
        return deny
    lot_id = int(hu.path_params(event)["id"])
    user_id = int(hu.claims(event)["user_id"])
    body = hu.json_body(event)

    certification = None
    if new_status == "accepted":
        certification = body.get("certification") or None
        if certification and certification not in db.CERTIFICATIONS:
            return hu.error(400, "Unknown certification.")

    with db.get_conn() as conn:
        # Verify this lot actually belongs to the caller's tenant and is
        # still pending *before* anything below touches lot_allocations -
        # lot ids are a single global SERIAL, so a lot_id from another
        # tenant is trivially guessable, and the conflict-check query a few
        # lines down would otherwise read (and potentially leak, in its
        # error message) another tenant's farmer names/volumes.
        owned = conn.execute(
            "SELECT 1 FROM lots WHERE id=%s AND lba_id=%s AND status='pending'",
            (lot_id, lba_id),
        ).fetchone()
        if not owned:
            return hu.error(409, "This lot is no longer pending review.")

        if new_status == "accepted":
            # Pending lots don't reserve quota (see _eligible_farmers), so
            # two different pending lots can each have been built against a
            # farmer's full remaining amount. This is the one place that's
            # actually checked - a farmer can never end up over-delivered
            # once accepted, even if accepting this lot is what finally
            # reveals the conflict with another already-accepted lot.
            conflicts = conn.execute(
                """
                SELECT f.farmer_code, f.full_name, f.potential_volume_kg, f.opening_delivered_kg,
                       a.allocated_volume_kg,
                       COALESCE((
                         SELECT SUM(a2.allocated_volume_kg) FROM lot_allocations a2
                         JOIN lots l2 ON l2.id = a2.lot_id
                         WHERE a2.farmer_id = f.id AND l2.status = 'accepted' AND l2.id != %s
                       ), 0) AS other_accepted
                FROM lot_allocations a
                JOIN farmers f ON f.id = a.farmer_id
                WHERE a.lot_id = %s
                """,
                (lot_id, lot_id),
            ).fetchall()
            over = [
                c for c in conflicts
                if c["opening_delivered_kg"] + c["other_accepted"] + c["allocated_volume_kg"]
                    > c["potential_volume_kg"] + 0.01
            ]
            if over:
                names = ", ".join(
                    f"{c['full_name']} ({c['farmer_code']}) by "
                    f"{round(c['opening_delivered_kg'] + c['other_accepted'] + c['allocated_volume_kg'] - c['potential_volume_kg'], 2):g}kg"
                    for c in over
                )
                return hu.error(
                    409,
                    f"Accepting this lot would push the following farmer(s) over their potential volume, "
                    f"likely because another lot for them was accepted in the meantime: {names}. "
                    f"Reject this lot or resolve the conflicting one first.",
                )

        cur = conn.execute(
            "UPDATE lots SET status=%s, reviewed_by=%s, reviewed_at=now(), certification=%s "
            "WHERE id=%s AND lba_id=%s AND status='pending' RETURNING id",
            (new_status, user_id, certification, lot_id, lba_id),
        )
        if not cur.fetchone():
            return hu.error(409, "This lot is no longer pending review.")
        db.log_audit(conn, lba_id, user_id, f"lot.{new_status}", "lot", lot_id,
                      db.CERTIFICATIONS.get(certification) if certification else None)
    return hu.ok({"ok": True, "status": new_status})


def _export(event, lba_id):
    lot_id = int(hu.path_params(event)["id"])
    with db.get_conn() as conn:
        org = conn.execute("SELECT name FROM lbas WHERE id=%s", (lba_id,)).fetchone()
        lot = conn.execute(
            """SELECT l.*, (SELECT COUNT(*) FROM lots l2 WHERE l2.lba_id=l.lba_id AND l2.id<=l.id) AS lot_no
               FROM lots l WHERE l.id=%s AND l.lba_id=%s""",
            (lot_id, lba_id),
        ).fetchone()
        if not lot:
            return hu.error(404, "Lot not found.")
        rows = conn.execute(
            """
            SELECT a.receipt_number, a.allocated_volume_kg, a.num_bags, a.gross_weight_kg,
                   a.delivered_date, f.farmer_code, f.full_name, f.farmer_uid
            FROM lot_allocations a JOIN farmers f ON f.id = a.farmer_id
            WHERE a.lot_id = %s ORDER BY a.receipt_number
            """,
            (lot_id,),
        ).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"LOT {lot['lot_no']}"
    ws.append(["WAREHOUSE DELIVERY SLIP"])
    ws.append(["CERTIFIED COCOA"])
    ws.append([])
    ws.append(["", "", lot["lot_no"]])
    ws.append([f"LBA'S NAME:>> {org['name']}", "LOT"])
    ws.append(["", "", "N° of Bags Declared", lot["bags_declared"] or ""])
    ws.append([f"VEHICLE PLATE NUMBER:>> {lot['vehicle_plate'] or ''}", "", "Net weight declared", lot["total_volume_kg"]])
    ws.append([f"ESCORT/DRIVERS NAME:>> {lot['driver_name'] or ''}", "", "Moisture/Humidity", lot["moisture_pct"] or ""])
    ws.append([f"DELIVERY DATE:>> {lot['lot_date']}"])
    ws.append([f"WAYBILL Number:>> {lot['waybill_number'] or ''}"])
    ws.append([f"STATUS:>> {lot['status'].upper()}"])
    ws.append([])
    ws.append(["FARMERS CODE", "FARMERS NAMES", "N° OF BAGS", "GROS WEIGHT (kg)",
               "NET WEIGHT (kg)", "RECIEPT NO", "DATE DELIVERED (mm/dd/yyyy)", "STATUS", "Farmer id"])
    for r in rows:
        ws.append([
            r["farmer_code"], r["full_name"], r["num_bags"] or "", r["gross_weight_kg"] or "",
            r["allocated_volume_kg"], r["receipt_number"], r["delivered_date"] or lot["lot_date"],
            "OK", r["farmer_uid"] or "",
        ])
    ws.append([])
    ws.append(["", "", "", "", sum(r["allocated_volume_kg"] for r in rows), "", "", "", "Total"])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    key = f"lot-exports/{lba_id}/lot_{lot['lot_no']}_delivery_slip.xlsx"
    _s3.put_object(
        Bucket=EXPORTS_BUCKET, Key=key, Body=buf.getvalue(),
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    url = _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": EXPORTS_BUCKET, "Key": key,
                "ResponseContentDisposition": f"attachment; filename=lot_{lot['lot_no']}_delivery_slip.xlsx"},
        ExpiresIn=300,
    )
    return hu.ok({"download_url": url})


RECEIPT_COPY_LABELS = ["ORIGINAL", "DUPLICATE 1", "DUPLICATE 2", "DUPLICATE 3"]


def _receipts(event, lba_id):
    """One printable farmer receipt per copy label (4 total: the original
    plus 3 duplicates - standard original-and-copies paper trail), only for
    an already-accepted lot. Each receipt is its own sheet so it prints as
    its own page."""
    deny = hu.require_role(event, ROLES_CAN_REVIEW_LOT)
    if deny:
        return deny
    lot_id = int(hu.path_params(event)["id"])
    with db.get_conn() as conn:
        org = conn.execute("SELECT name FROM lbas WHERE id=%s", (lba_id,)).fetchone()
        lot = conn.execute(
            """SELECT l.*, (SELECT COUNT(*) FROM lots l2 WHERE l2.lba_id=l.lba_id AND l2.id<=l.id) AS lot_no
               FROM lots l WHERE l.id=%s AND l.lba_id=%s""",
            (lot_id, lba_id),
        ).fetchone()
        if not lot:
            return hu.error(404, "Lot not found.")
        if lot["status"] != "accepted":
            return hu.error(400, "Receipts can only be generated for an accepted lot.")
        rows = conn.execute(
            """
            SELECT a.receipt_number, a.allocated_volume_kg, a.num_bags,
                   COALESCE(a.delivered_date, l.lot_date) AS delivered_date,
                   f.farmer_code, f.full_name, f.community
            FROM lot_allocations a JOIN farmers f ON f.id = a.farmer_id JOIN lots l ON l.id = a.lot_id
            WHERE a.lot_id = %s ORDER BY a.receipt_number
            """,
            (lot_id,),
        ).fetchall()

    cert_label = db.CERTIFICATIONS.get(lot["certification"]) if lot["certification"] else "—"

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for r in rows:
        ws = wb.create_sheet(f"{r['receipt_number']}"[:31])
        for copy_label in RECEIPT_COPY_LABELS:
            ws.append(["FARMER RECEIPT", "", copy_label])
            ws.append([f"LBA: {org['name']}", "", f"Lot #{lot['lot_no']}"])
            ws.append([f"Certification: {cert_label}"])
            ws.append([])
            ws.append(["Farmer code", r["farmer_code"]])
            ws.append(["Farmer name", r["full_name"]])
            ws.append(["Community", r["community"] or ""])
            ws.append(["Receipt no.", r["receipt_number"]])
            ws.append(["Date delivered", r["delivered_date"]])
            ws.append(["Bags", r["num_bags"] or ""])
            ws.append(["Net weight (kg)", r["allocated_volume_kg"]])
            ws.append(["Farmer signature", "______________________"])
            ws.append([])
            ws.append([])

    buf = io.BytesIO()
    wb.save(buf)

    key = f"lot-receipts/{lba_id}/lot_{lot['lot_no']}_receipts.xlsx"
    _s3.put_object(
        Bucket=EXPORTS_BUCKET, Key=key, Body=buf.getvalue(),
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    url = _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": EXPORTS_BUCKET, "Key": key,
                "ResponseContentDisposition": f"attachment; filename=lot_{lot['lot_no']}_receipts.xlsx"},
        ExpiresIn=300,
    )

    with db.get_conn() as conn:
        db.log_audit(conn, lba_id, int(hu.claims(event)["user_id"]), "lot.receipts_generated", "lot", lot_id,
                      f"{len(rows)} farmer(s) x {len(RECEIPT_COPY_LABELS)} copies")

    return hu.ok({"download_url": url})
