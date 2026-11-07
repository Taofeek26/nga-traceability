"""Supporting traceability documents (certificates, etc.) - any file type,
stored in S3 with a DB row for listing/metadata. Open to every role: any
of the three roles might be the one holding the certificate that needs
uploading.
"""
import os
import time
import uuid

import boto3

import db
import http_util as hu
import multipart_util

_s3 = boto3.client("s3")
DOCUMENTS_BUCKET = os.environ.get("DOCUMENTS_BUCKET")


def lambda_handler(event, context):
    m = hu.method(event)
    path = event["rawPath"]
    lba_id = int(hu.claims(event)["lba_id"])

    if path.endswith("/download"):
        return _download(event, lba_id)
    if m == "POST":
        return _upload(event, lba_id)
    if m == "DELETE":
        return _delete(event, lba_id)
    if m == "GET":
        return _list(lba_id)
    return hu.error(404, "Not found")


def _list(lba_id):
    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT d.id, d.filename, d.content_type, d.size_bytes, d.note, d.created_at,
                   u.name AS uploaded_by_name
            FROM documents d
            LEFT JOIN users u ON u.id = d.uploaded_by
            WHERE d.lba_id = %s
            ORDER BY d.created_at DESC
            """,
            (lba_id,),
        ).fetchall()
    return hu.ok({"documents": rows})


def _upload(event, lba_id):
    filename, content = multipart_util.parse_single_file(event)
    if content is None:
        return hu.error(400, "No file uploaded.")
    user_id = int(hu.claims(event)["user_id"])

    safe_name = os.path.basename(filename or "document")
    key = f"{lba_id}/{int(time.time())}-{uuid.uuid4().hex[:8]}-{safe_name}"
    _s3.put_object(Bucket=DOCUMENTS_BUCKET, Key=key, Body=content)

    with db.get_conn() as conn:
        row = conn.execute(
            """INSERT INTO documents (lba_id, uploaded_by, filename, s3_key, content_type, size_bytes)
               VALUES (%s,%s,%s,%s,%s,%s) RETURNING id, filename, content_type, size_bytes, created_at""",
            (lba_id, user_id, safe_name, key, None, len(content)),
        ).fetchone()
        db.log_audit(conn, lba_id, user_id, "document.uploaded", "document", row["id"], safe_name)

    return hu.created({"document": row})


def _download(event, lba_id):
    doc_id = int(hu.path_params(event)["id"])
    with db.get_conn() as conn:
        doc = conn.execute(
            "SELECT s3_key, filename FROM documents WHERE id=%s AND lba_id=%s", (doc_id, lba_id)
        ).fetchone()
    if not doc:
        return hu.error(404, "Document not found.")
    url = _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": DOCUMENTS_BUCKET, "Key": doc["s3_key"],
                "ResponseContentDisposition": f'attachment; filename="{doc["filename"]}"'},
        ExpiresIn=300,
    )
    return hu.ok({"download_url": url})


def _delete(event, lba_id):
    doc_id = int(hu.path_params(event)["id"])
    user_id = int(hu.claims(event)["user_id"])
    with db.get_conn() as conn:
        doc = conn.execute(
            "SELECT s3_key, filename FROM documents WHERE id=%s AND lba_id=%s", (doc_id, lba_id)
        ).fetchone()
        if not doc:
            return hu.error(404, "Document not found.")
        conn.execute("DELETE FROM documents WHERE id=%s AND lba_id=%s", (doc_id, lba_id))
        db.log_audit(conn, lba_id, user_id, "document.deleted", "document", doc_id, doc["filename"])
    _s3.delete_object(Bucket=DOCUMENTS_BUCKET, Key=doc["s3_key"])
    return hu.ok({"ok": True})
