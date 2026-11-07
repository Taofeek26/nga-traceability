"""Farmer register: upload, list/detail, incentives, export, clear-all.

Ported from app.py's /upload, /upload/template, /farmers*, /data/clear.
Same HEADER_ALIASES/_norm_header matching the original app validates
against. Downloads (template, export) go through S3 + a presigned URL
instead of streaming through API Gateway - see
html/frontend-backend-split-plan.html §7.2.
"""
import io
import os
import re
from datetime import date, datetime

import boto3
import openpyxl
import psycopg2.errors

import db
import http_util as hu
import multipart_util

ADMIN_ONLY = {"admin"}
_s3 = boto3.client("s3")
TEMPLATES_BUCKET = os.environ.get("TEMPLATES_BUCKET")
EXPORTS_BUCKET = os.environ.get("EXPORTS_BUCKET")

HEADER_ALIASES = {
    "farmer_code": "farmer_code", "farmers_code": "farmer_code",
    "full_name": "full_name", "farmer_full_name": "full_name",
    "farmers_names": "full_name", "farmer_name": "full_name", "name": "full_name",
    "first_name": "first_name", "surname": "surname", "last_name": "surname",
    "farmer_id": "farmer_uid", "farmer_uid": "farmer_uid",
    "gender": "gender",
    "date_of_birth": "date_of_birth", "dob": "date_of_birth",
    "phone_number": "phone_number", "phone": "phone_number",
    "nin": "nin",
    "community": "community", "community_name": "community",
    "num_plots": "num_plots", "number_of_plots": "num_plots",
    "farm_size_ha": "farm_size_ha", "total_farm_size_mapped_ha": "farm_size_ha",
    "potential_volume_kg": "potential_volume_kg", "potential_volume": "potential_volume_kg",
    # A farmer register that was tracked manually (in Excel, say) before
    # moving onto this system - or a previous export from this system,
    # re-uploaded - already has a "Net Weight" column: what's actually been
    # delivered so far. Treated as an opening balance on top of whatever
    # gets allocated through lots going forward, so migrating mid-season
    # doesn't require recreating every historical delivery as a lot.
    "net_weight_kg": "opening_delivered_kg", "net_weight": "opening_delivered_kg",
    "net_wt_kg": "opening_delivered_kg", "delivered_kg": "opening_delivered_kg",
    # Variance is always recomputed from potential - delivered wherever
    # it's shown (export, dashboard, farmer list) rather than stored, so a
    # Variance column already present in a re-uploaded export is harmless
    # and simply ignored - it'll be right again the moment Net Weight is.
}


def _norm_header(h):
    h = str(h or "").strip().lower()
    h = re.sub(r"[^\w\s]", "", h)
    h = re.sub(r"\s+", "_", h).strip("_")
    return h


def lambda_handler(event, context):
    m = hu.method(event)
    path = event["rawPath"]
    lba_id = int(hu.claims(event)["lba_id"])

    if path.endswith("/upload-template"):
        return _upload_template(event)
    if path.endswith("/upload"):
        return _upload_master_data(event, lba_id)
    if path.endswith("/export"):
        return _export(lba_id)
    if path.endswith("/clear-all"):
        return _clear_all(event, lba_id)
    if path.endswith("/incentives"):
        return _add_incentive(event, lba_id)
    if path.endswith("/toggle-active"):
        return _toggle_active(event, lba_id)
    if m == "GET" and hu.path_params(event).get("code"):
        return _detail(event, lba_id)
    if m == "GET":
        return _list(event, lba_id)
    return hu.error(404, "Not found")


def _upload_template(event):
    deny = hu.require_role(event, ADMIN_ONLY)
    if deny:
        return deny
    # v2: adds the optional "Net Weight (Kg)" column - bumped so a stale
    # v1 object already cached in S3 from before this column existed
    # doesn't keep being served as-is.
    key = "farmer_master_data_template_v2.xlsx"
    try:
        _s3.head_object(Bucket=TEMPLATES_BUCKET, Key=key)
    except _s3.exceptions.ClientError:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Farmers"
        ws.append(["Farmer Code", "Farmer Full name", "Farmer id", "Gender", "Date of birth",
                   "Phone number", "NIN", "Community Name", "Num plots", "Total Farm Size Mapped (Ha)",
                   "Potential Volume", "Net Weight (Kg)"])
        ws.append(["JIM-OD-OS-14-0002", "Chinedu Okafor", 1473737, "M", "1985-04-12",
                   "08012345678", "12345678901", "Agbor Community", 2, 3.5, 2100, 0])
        ws.append([])
        ws.append(["Net Weight (Kg) is optional - fill it in only if a farmer already has delivery "
                    "history from before you started using this system (e.g. a register you tracked "
                    "manually, or a previous export from here). Leave it at 0, or leave the column "
                    "out entirely, for a farmer with no prior delivery history."])
        buf = io.BytesIO()
        wb.save(buf)
        _s3.put_object(
            Bucket=TEMPLATES_BUCKET, Key=key, Body=buf.getvalue(),
            ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    url = _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": TEMPLATES_BUCKET, "Key": key,
                "ResponseContentDisposition": "attachment; filename=farmer_master_data_template.xlsx"},
        ExpiresIn=300,
    )
    return hu.ok({"download_url": url})


def _upload_master_data(event, lba_id):
    deny = hu.require_role(event, ADMIN_ONLY)
    if deny:
        return deny
    filename, content = multipart_util.parse_single_file(event)
    if content is None:
        return hu.error(400, "No file uploaded.")
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    except Exception:
        return hu.error(400, "Could not read that file. Please upload a .xlsx file.")
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return hu.error(400, "The file is empty.")

    raw_header = [_norm_header(h) for h in rows[0]]
    header = [HEADER_ALIASES.get(h, h) for h in raw_header]
    has_full_name = "full_name" in header
    has_split_name = "first_name" in header and "surname" in header
    missing = [c for c in ("farmer_code", "potential_volume_kg") if c not in header]
    if not (has_full_name or has_split_name):
        missing.append("full_name (or first_name + surname)")
    if missing:
        return hu.error(400, f"Missing required column(s): {','.join(missing)}. "
                              f"Download the template from this page for the exact headers.")
    col_idx = {}
    for i, name in enumerate(header):
        if name:
            col_idx.setdefault(name, i)
    has_net_weight = "opening_delivered_kg" in col_idx

    inserted, updated, skipped = 0, 0, 0
    with db.get_conn() as conn:
        for row in rows[1:]:
            if row is None or all(v is None for v in row):
                continue

            def val(name, default=None):
                idx = col_idx.get(name)
                if idx is None or idx >= len(row):
                    return default
                v = row[idx]
                return default if v is None else v

            code = str(val("farmer_code", "")).strip()
            if not code:
                skipped += 1
                continue

            if has_full_name:
                full_name = str(val("full_name", "")).strip()
            else:
                full_name = f"{val('first_name', '')} {val('surname', '')}".strip()
            if not full_name:
                full_name = code

            dob = val("date_of_birth")
            if isinstance(dob, (datetime, date)):
                dob = dob.isoformat()
            farmer_uid = val("farmer_uid")
            if farmer_uid is not None:
                farmer_uid = str(farmer_uid).strip()

            existing = conn.execute(
                "SELECT id FROM farmers WHERE lba_id=%s AND farmer_code=%s", (lba_id, code)
            ).fetchone()
            params = (
                full_name,
                farmer_uid or None,
                str(val("gender", "")).strip() or None,
                str(dob) if dob else None,
                str(val("phone_number", "")).strip() or None,
                str(val("nin", "")).strip() or None,
                str(val("community", "")).strip() or None,
                int(val("num_plots", 0) or 0),
                float(val("farm_size_ha", 0) or 0),
                float(val("potential_volume_kg", 0) or 0),
            )
            if existing:
                if has_net_weight:
                    # The uploaded Net Weight is a TOTAL-delivered-to-date
                    # figure (that's what it means in the yield-monitoring
                    # export this same column comes from), not an addend -
                    # so back it out against whatever this farmer already
                    # has recorded through accepted lots, rather than
                    # setting opening_delivered_kg to the raw figure. That
                    # way re-uploading a later export of a farmer who has
                    # since had real lots accepted doesn't double-count
                    # those lots: opening + lot_sum still equals the
                    # uploaded total.
                    lot_sum = conn.execute(
                        """SELECT COALESCE(SUM(a.allocated_volume_kg), 0) s FROM lot_allocations a
                           JOIN lots l ON l.id = a.lot_id
                           WHERE a.farmer_id=%s AND l.status='accepted'""",
                        (existing["id"],),
                    ).fetchone()["s"]
                    net_weight = float(val("opening_delivered_kg", 0) or 0)
                    opening = max(0.0, net_weight - lot_sum)
                    conn.execute(
                        """UPDATE farmers SET full_name=%s, farmer_uid=%s, gender=%s, date_of_birth=%s,
                           phone_number=%s, nin=%s, community=%s, num_plots=%s, farm_size_ha=%s,
                           potential_volume_kg=%s, opening_delivered_kg=%s, updated_at=now()
                           WHERE lba_id=%s AND farmer_code=%s""",
                        params + (opening, lba_id, code),
                    )
                else:
                    # No Net Weight column in this file at all - leave
                    # whatever opening balance this farmer already has
                    # alone rather than resetting it to zero. Unlike the
                    # other optional columns, this one feeds quota math
                    # directly, so a routine re-upload on the plain
                    # template (which never has this column) must not
                    # silently erase a previously migrated register.
                    conn.execute(
                        """UPDATE farmers SET full_name=%s, farmer_uid=%s, gender=%s, date_of_birth=%s,
                           phone_number=%s, nin=%s, community=%s, num_plots=%s, farm_size_ha=%s,
                           potential_volume_kg=%s, updated_at=now()
                           WHERE lba_id=%s AND farmer_code=%s""",
                        params + (lba_id, code),
                    )
                updated += 1
            else:
                # Brand new farmer - no lot history can possibly exist yet,
                # so the uploaded Net Weight (if any) *is* the opening
                # balance outright.
                opening = max(0.0, float(val("opening_delivered_kg", 0) or 0))
                conn.execute(
                    """INSERT INTO farmers (lba_id, farmer_code, full_name, farmer_uid, gender,
                       date_of_birth, phone_number, nin, community, num_plots,
                       farm_size_ha, potential_volume_kg, opening_delivered_kg)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (lba_id, code) + params + (opening,),
                )
                inserted += 1

        db.log_audit(conn, lba_id, int(hu.claims(event)["user_id"]), "farmers.uploaded", "farmer", None,
                      f"{inserted} added, {updated} updated, {skipped} skipped")

    return hu.ok({"inserted": inserted, "updated": updated, "skipped": skipped})


def _list(event, lba_id):
    q = hu.query_params(event).get("q", "")
    with db.get_conn() as conn:
        like = f"%{q}%" if q else None
        where = "f.lba_id=%s" + (
            " AND (f.farmer_code ILIKE %s OR f.full_name ILIKE %s OR f.community ILIKE %s)" if q else ""
        )
        params = (lba_id, like, like, like) if q else (lba_id,)
        rows = conn.execute(
            f"""
            SELECT f.*, f.opening_delivered_kg
                + COALESCE(SUM(a.allocated_volume_kg) FILTER (WHERE l.status = 'accepted'), 0) delivered
            FROM farmers f
            LEFT JOIN lot_allocations a ON a.farmer_id = f.id
            LEFT JOIN lots l ON l.id = a.lot_id
            WHERE {where}
            GROUP BY f.id ORDER BY f.full_name
            """,
            params,
        ).fetchall()
    return hu.ok({"farmers": rows, "q": q})


def _detail(event, lba_id):
    code = hu.path_params(event)["code"]
    with db.get_conn() as conn:
        farmer = conn.execute(
            "SELECT * FROM farmers WHERE lba_id=%s AND farmer_code=%s", (lba_id, code)
        ).fetchone()
        if not farmer:
            return hu.error(404, "Farmer not found.")
        deliveries = conn.execute(
            """
            SELECT l.id lot_id, COALESCE(a.delivered_date, l.lot_date) AS lot_date, l.status,
                   a.receipt_number, a.allocated_volume_kg
            FROM lot_allocations a JOIN lots l ON l.id = a.lot_id
            WHERE a.farmer_id = %s ORDER BY lot_date DESC, l.id DESC
            """,
            (farmer["id"],),
        ).fetchall()
        # opening_delivered_kg is whatever had already been delivered before
        # this farmer was tracked here - carried over from a manually-kept
        # register (or a previous export) that already had a Net Weight
        # column filled in at upload time.
        delivered = farmer["opening_delivered_kg"] + sum(
            d["allocated_volume_kg"] for d in deliveries if d["status"] == "accepted"
        )
        pending = sum(d["allocated_volume_kg"] for d in deliveries if d["status"] == "pending")
        incentives = conn.execute(
            "SELECT * FROM incentives WHERE farmer_id=%s ORDER BY incentive_date DESC, id DESC",
            (farmer["id"],),
        ).fetchall()
        premium_rate = float(db.get_setting(lba_id, "premium_rate_per_kg", "0") or 0)
    premium_accrued = round(delivered * premium_rate, 2)
    other_incentives = sum(i["amount"] for i in incentives)
    return hu.ok({
        "farmer": farmer,
        "deliveries": deliveries,
        "delivered": delivered,
        "pending": pending,
        # Pending deliveries no longer reserve quota (see lot_service's
        # _eligible_farmers) - only accepted volume counts against potential.
        "remaining": farmer["potential_volume_kg"] - delivered,
        "incentives": incentives,
        "premium_rate": premium_rate,
        "premium_accrued": premium_accrued,
        "other_incentives": other_incentives,
        "total_entitlement": premium_accrued + other_incentives,
    })


def _add_incentive(event, lba_id):
    deny = hu.require_role(event, ADMIN_ONLY)
    if deny:
        return deny
    code = hu.path_params(event)["code"]
    body = hu.json_body(event)
    with db.get_conn() as conn:
        farmer = conn.execute(
            "SELECT id FROM farmers WHERE lba_id=%s AND farmer_code=%s", (lba_id, code)
        ).fetchone()
        if not farmer:
            return hu.error(404, "Farmer not found.")
        conn.execute(
            "INSERT INTO incentives (farmer_id, type, amount, incentive_date, note) "
            "VALUES (%s,%s,%s,%s,%s)",
            (farmer["id"], body.get("type"), body.get("amount"), body.get("incentive_date"), body.get("note", "")),
        )
    return hu.created({"ok": True})


def _toggle_active(event, lba_id):
    deny = hu.require_role(event, ADMIN_ONLY)
    if deny:
        return deny
    code = hu.path_params(event)["code"]
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE farmers SET active = NOT active, updated_at=now() WHERE lba_id=%s AND farmer_code=%s",
            (lba_id, code),
        )
    return hu.ok({"ok": True})


def _export(lba_id):
    with db.get_conn() as conn:
        org = conn.execute("SELECT name FROM lbas WHERE id=%s", (lba_id,)).fetchone()
        premium_rate = float(db.get_setting(lba_id, "premium_rate_per_kg", "0") or 0)
        rows = conn.execute(
            """
            SELECT f.farmer_code, f.full_name, f.gender, f.community, f.farm_size_ha,
                   f.potential_volume_kg, f.farmer_uid, f.active,
                   f.opening_delivered_kg
                       + COALESCE(SUM(a.allocated_volume_kg) FILTER (WHERE l.status = 'accepted'), 0) AS delivered
            FROM farmers f
            LEFT JOIN lot_allocations a ON a.farmer_id = f.id
            LEFT JOIN lots l ON l.id = a.lot_id
            WHERE f.lba_id=%s
            GROUP BY f.id
            ORDER BY f.full_name
            """,
            (lba_id,),
        ).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Yield Monitoring"
    ws.append(["YIELD CONTROL AND BENCHMARK ANALYSIS"])
    ws.append(["LBA", "Farmer Code", "Farmer Full name", "Gender", "Community Name",
               "Net Weight (Kg)", "Total Farm Size Mapped (Ha)", "Potential Volume",
               "Variance (kg)", "Variance (%)", "STATUS", "Farmer id", "Premium (NGN)"])
    for r in rows:
        remaining = r["potential_volume_kg"] - r["delivered"]
        pct = (r["delivered"] / r["potential_volume_kg"]) if r["potential_volume_kg"] else 0
        if not r["active"]:
            status = "INACTIVE"
        elif pct >= 1:
            status = "AT LIMIT"
        elif pct >= 0.9:
            status = "NEAR LIMIT"
        else:
            status = "OK"
        premium = round(r["delivered"] * premium_rate, 2)
        ws.append([
            org["name"], r["farmer_code"], r["full_name"], r["gender"] or "", r["community"] or "",
            r["delivered"], r["farm_size_ha"], r["potential_volume_kg"],
            remaining, round(pct, 4), status, r["farmer_uid"] or "", premium,
        ])
    buf = io.BytesIO()
    wb.save(buf)

    key = f"farmer-exports/{lba_id}/yield_monitoring_export.xlsx"
    _s3.put_object(
        Bucket=EXPORTS_BUCKET, Key=key, Body=buf.getvalue(),
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    url = _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": EXPORTS_BUCKET, "Key": key,
                "ResponseContentDisposition": "attachment; filename=yield_monitoring_export.xlsx"},
        ExpiresIn=300,
    )
    return hu.ok({"download_url": url})


def _clear_all(event, lba_id):
    deny = hu.require_role(event, ADMIN_ONLY)
    if deny:
        return deny
    body = hu.json_body(event)
    if body.get("confirm") != "CLEAR":
        return hu.error(400, "Type CLEAR exactly to confirm.")
    db.wipe_lba_data(lba_id)
    with db.get_conn() as conn:
        db.log_audit(conn, lba_id, int(hu.claims(event)["user_id"]), "data.cleared", "lba", lba_id, None)
    return hu.ok({"ok": True})
