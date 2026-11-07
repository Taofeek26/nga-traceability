"""Season backup/restore: a full snapshot of one LBA's farmer/lot data,
taken automatically right before "Clear all data" wipes it, so a
finished season can still be looked back on (or brought back) later.

Scope matches db.wipe_lba_data() exactly: farmers, lots,
lot_allocations, incentives. Settings and documents aren't touched by
clear-all, so they aren't part of the snapshot either.

The archive is a zip of plain JSON files (manifest.json, farmers.json,
lots.json, lot_allocations.json, incentives.json) - no DB-specific
format, so it's inspectable by just unzipping it. Foreign keys inside
the JSON use each table's REAL id from before the wipe (as "id"); on
restore those are remapped to freshly INSERTed ids, since the old ids
may already be taken by whatever's been created since.
"""
import io
import json
import zipfile
from datetime import date, datetime

SEASON_BACKUPS_PREFIX = "season-backups"


def _row_to_plain(row):
    return {k: (v.isoformat() if isinstance(v, (date, datetime)) else v) for k, v in dict(row).items()}


def _season_start(conn, lba_id):
    r = conn.execute(
        "SELECT MIN(created_at) t FROM audit_log WHERE lba_id=%s AND action='farmers.uploaded'",
        (lba_id,),
    ).fetchone()
    if r and r["t"]:
        return r["t"].date().isoformat()
    r = conn.execute("SELECT MIN(created_at) t FROM farmers WHERE lba_id=%s", (lba_id,)).fetchone()
    if r and r["t"]:
        return r["t"].date().isoformat()
    return date.today().isoformat()


def create_backup(conn, s3, bucket, lba_id, created_by_user_id):
    """Snapshot this lba's current farmer/lot data to S3 and record it in
    season_backups. Returns None (does nothing) if there's no data worth
    keeping - an admin clearing an already-empty register shouldn't leave
    a zero-row backup behind."""
    farmers = conn.execute("SELECT * FROM farmers WHERE lba_id=%s", (lba_id,)).fetchall()
    lots = conn.execute("SELECT * FROM lots WHERE lba_id=%s", (lba_id,)).fetchall()
    if not farmers and not lots:
        return None

    farmer_ids = [f["id"] for f in farmers]
    lot_ids = [l["id"] for l in lots]
    allocations = conn.execute(
        "SELECT * FROM lot_allocations WHERE lot_id = ANY(%s)", (lot_ids,)
    ).fetchall() if lot_ids else []
    incentives = conn.execute(
        "SELECT * FROM incentives WHERE farmer_id = ANY(%s)", (farmer_ids,)
    ).fetchall() if farmer_ids else []

    org = conn.execute("SELECT name FROM lbas WHERE id=%s", (lba_id,)).fetchone()
    season_start = _season_start(conn, lba_id)
    season_end = date.today().isoformat()

    manifest = {
        "lba_id": lba_id,
        "lba_name": org["name"] if org else None,
        "season_start": season_start,
        "season_end": season_end,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "n_farmers": len(farmers),
        "n_lots": len(lots),
        "n_lot_allocations": len(allocations),
        "n_incentives": len(incentives),
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("farmers.json", json.dumps([_row_to_plain(r) for r in farmers]))
        zf.writestr("lots.json", json.dumps([_row_to_plain(r) for r in lots]))
        zf.writestr("lot_allocations.json", json.dumps([_row_to_plain(r) for r in allocations]))
        zf.writestr("incentives.json", json.dumps([_row_to_plain(r) for r in incentives]))
    body = buf.getvalue()

    key = f"{SEASON_BACKUPS_PREFIX}/{lba_id}/{season_start}_to_{season_end}.zip"
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/zip")

    row = conn.execute(
        """INSERT INTO season_backups
           (lba_id, s3_key, season_start, season_end, n_farmers, n_lots, size_bytes, created_by)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (lba_id, key, season_start, season_end, len(farmers), len(lots), len(body), created_by_user_id),
    ).fetchone()
    return {"id": row["id"], "s3_key": key, **manifest}


# Explicit column allow-lists for restore, rather than trusting whatever
# keys happen to be in the backup's JSON - the SQL below interpolates
# column names (psycopg2 can only parameterize values), so this is what
# keeps that safe. Also fails predictably if the schema has drifted
# since the backup was taken, instead of silently doing whatever the
# file says.
_FARMER_COLS = ["farmer_code", "full_name", "farmer_uid", "gender", "date_of_birth",
                "phone_number", "nin", "community", "num_plots", "farm_size_ha",
                "potential_volume_kg", "opening_delivered_kg", "active"]
_LOT_COLS = ["lot_date", "total_volume_kg", "receipt_start", "receipt_end", "note", "status",
             "vehicle_plate", "driver_name", "waybill_number", "bags_declared", "moisture_pct",
             "certification", "reviewed_by", "reviewed_at"]
_ALLOCATION_COLS = ["receipt_number", "allocated_volume_kg", "num_bags", "gross_weight_kg",
                    "delivered_date"]
_INCENTIVE_COLS = ["type", "amount", "incentive_date", "note"]


_CHUNK = 500  # rows per INSERT - a season can easily have 1000s of farmers,
              # and the API Gateway integration has its own hard ~29s cap
              # independent of the Lambda's own timeout, so one INSERT per
              # row isn't an option at that scale.


def _bulk_insert(conn, table, rows, cols, returning=False, chunk=_CHUNK):
    """rows: a list of dicts already holding exactly `cols`' values (fixed
    columns like lba_id, or remapped FKs like farmer_id, included by the
    caller). Returns, if returning, the new ids in the SAME order as
    `rows` - Postgres guarantees a multi-row INSERT's RETURNING output
    follows the VALUES order."""
    new_ids = [] if returning else None
    col_list = ", ".join(cols)
    row_placeholder = "(" + ", ".join(["%s"] * len(cols)) + ")"
    for start in range(0, len(rows), chunk):
        batch = rows[start:start + chunk]
        sql = f"INSERT INTO {table} ({col_list}) VALUES " + ", ".join([row_placeholder] * len(batch))
        if returning:
            sql += " RETURNING id"
        values = [r[c] for r in batch for c in cols]
        cur = conn.execute(sql, values)
        if returning:
            new_ids.extend(r["id"] for r in cur.fetchall())
    return new_ids


def restore_backup(conn, s3, bucket, lba_id, backup_row):
    """Re-inserts a previously backed-up season's farmers/lots/
    allocations/incentives as fresh rows (new ids - the old ones may be
    reused by now), remapping foreign keys as it goes. Caller is
    responsible for only allowing this when it's actually safe to (see
    season_backup_service's check that the live register is empty)."""
    obj = s3.get_object(Bucket=bucket, Key=backup_row["s3_key"])
    with zipfile.ZipFile(io.BytesIO(obj["Body"].read())) as zf:
        farmers = json.loads(zf.read("farmers.json"))
        lots = json.loads(zf.read("lots.json"))
        allocations = json.loads(zf.read("lot_allocations.json"))
        incentives = json.loads(zf.read("incentives.json"))

    farmer_id_map = {}
    if farmers:
        cols = ["lba_id"] + [c for c in _FARMER_COLS if c in farmers[0]]
        rows = [dict(f, lba_id=lba_id) for f in farmers]
        new_ids = _bulk_insert(conn, "farmers", rows, cols, returning=True)
        farmer_id_map = dict(zip((f["id"] for f in farmers), new_ids))

    lot_id_map = {}
    if lots:
        cols = ["lba_id"] + [c for c in _LOT_COLS if c in lots[0]]
        rows = [dict(l, lba_id=lba_id) for l in lots]
        new_ids = _bulk_insert(conn, "lots", rows, cols, returning=True)
        lot_id_map = dict(zip((l["id"] for l in lots), new_ids))

    if allocations:
        cols = ["farmer_id", "lot_id"] + [c for c in _ALLOCATION_COLS if c in allocations[0]]
        rows = []
        for a in allocations:
            new_farmer_id = farmer_id_map.get(a["farmer_id"])
            new_lot_id = lot_id_map.get(a["lot_id"])
            if new_farmer_id is None or new_lot_id is None:
                continue
            rows.append(dict(a, farmer_id=new_farmer_id, lot_id=new_lot_id))
        _bulk_insert(conn, "lot_allocations", rows, cols)

    if incentives:
        cols = ["farmer_id"] + [c for c in _INCENTIVE_COLS if c in incentives[0]]
        rows = []
        for i in incentives:
            new_farmer_id = farmer_id_map.get(i["farmer_id"])
            if new_farmer_id is None:
                continue
            rows.append(dict(i, farmer_id=new_farmer_id))
        _bulk_insert(conn, "incentives", rows, cols)

    conn.execute("UPDATE season_backups SET restored_at=now() WHERE id=%s", (backup_row["id"],))
    return {"n_farmers": len(farmers), "n_lots": len(lots), "n_lot_allocations": len(allocations),
            "n_incentives": len(incentives)}
