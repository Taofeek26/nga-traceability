"""List, download and restore the season snapshots clear-all takes
automatically before wiping a farmer register (see
layers/common/season_backup.py and farmer_register_service's
_clear_all). Admin-only - these are whole-season, account-wide
operations, same tier as clear-all itself.
"""
import os

import boto3

import db
import http_util as hu
import season_backup

ADMIN_ONLY = {"admin"}
_s3 = boto3.client("s3")
DOCUMENTS_BUCKET = os.environ.get("DOCUMENTS_BUCKET")


def lambda_handler(event, context):
    deny = hu.require_role(event, ADMIN_ONLY)
    if deny:
        return deny
    m = hu.method(event)
    lba_id = int(hu.claims(event)["lba_id"])
    path = event["rawPath"]
    backup_id = hu.path_params(event).get("id")

    if m == "GET" and path.endswith("/download"):
        return _download(lba_id, backup_id)
    if m == "POST" and path.endswith("/restore"):
        return _restore(event, lba_id, backup_id)
    if m == "GET":
        return _list(lba_id)
    return hu.error(404, "Not found")


def _list(lba_id):
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM season_backups WHERE lba_id=%s ORDER BY id DESC", (lba_id,)
        ).fetchall()
        n_live_farmers = conn.execute(
            "SELECT COUNT(*) c FROM farmers WHERE lba_id=%s", (lba_id,)
        ).fetchone()["c"]
    return hu.ok({"backups": rows, "register_is_empty": n_live_farmers == 0})


def _get_owned_backup(conn, lba_id, backup_id):
    try:
        backup_id = int(backup_id)
    except (TypeError, ValueError):
        return None
    return conn.execute(
        "SELECT * FROM season_backups WHERE id=%s AND lba_id=%s", (backup_id, lba_id)
    ).fetchone()


def _download(lba_id, backup_id):
    with db.get_conn() as conn:
        backup = _get_owned_backup(conn, lba_id, backup_id)
    if not backup:
        return hu.error(404, "Backup not found.")
    url = _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": DOCUMENTS_BUCKET, "Key": backup["s3_key"],
                "ResponseContentDisposition":
                    f"attachment; filename=season_{backup['season_start']}_to_{backup['season_end']}.zip"},
        ExpiresIn=300,
    )
    return hu.ok({"download_url": url})


def _restore(event, lba_id, backup_id):
    with db.get_conn() as conn:
        backup = _get_owned_backup(conn, lba_id, backup_id)
        if not backup:
            return hu.error(404, "Backup not found.")
        n_live_farmers = conn.execute(
            "SELECT COUNT(*) c FROM farmers WHERE lba_id=%s", (lba_id,)
        ).fetchone()["c"]
        if n_live_farmers > 0:
            return hu.error(
                409,
                "Your current register isn't empty. Restoring a past season would mix it with what's "
                "there now - clear the current data first (which backs it up the same way) if you "
                "need to bring this one back.",
            )
        result = season_backup.restore_backup(conn, _s3, DOCUMENTS_BUCKET, lba_id, backup)
        db.log_audit(
            conn, lba_id, int(hu.claims(event)["user_id"]), "data.restored", "season_backup", backup_id,
            f"{backup['season_start']} to {backup['season_end']}: "
            f"{result['n_farmers']} farmers, {result['n_lots']} lots",
        )
    return hu.ok({"ok": True, **result})
