"""Postgres access layer - ported from the original app's database.py.

Schema, migrations, and backfills are unchanged from the Vercel+Neon app.
The only real difference is where the connection string comes from: the
Aurora cluster's AWS-managed master-user secret (DB_SECRET_ARN), fetched
once per cold start and cached, instead of a DATABASE_URL env var.
"""
import json
import os
from contextlib import contextmanager

import boto3
import psycopg2
import psycopg2.extras

_secrets_client = boto3.client("secretsmanager")
_cached_dsn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS lbas (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    lba_id INTEGER NOT NULL REFERENCES lbas(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin' CHECK (role IN ('admin', 'to', 'lba')),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS farmers (
    id SERIAL PRIMARY KEY,
    lba_id INTEGER NOT NULL REFERENCES lbas(id) ON DELETE CASCADE,
    farmer_code TEXT NOT NULL,
    full_name TEXT NOT NULL,
    farmer_uid TEXT,
    gender TEXT,
    date_of_birth TEXT,
    phone_number TEXT,
    nin TEXT,
    community TEXT,
    num_plots INTEGER DEFAULT 0,
    farm_size_ha REAL DEFAULT 0,
    potential_volume_kg REAL NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (lba_id, farmer_code)
);

CREATE TABLE IF NOT EXISTS lots (
    id SERIAL PRIMARY KEY,
    lba_id INTEGER NOT NULL REFERENCES lbas(id) ON DELETE CASCADE,
    lot_date TEXT NOT NULL,
    total_volume_kg REAL NOT NULL,
    receipt_start INTEGER NOT NULL,
    receipt_end INTEGER NOT NULL,
    note TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
    vehicle_plate TEXT,
    driver_name TEXT,
    waybill_number TEXT,
    bags_declared INTEGER,
    moisture_pct REAL,
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lot_allocations (
    id SERIAL PRIMARY KEY,
    lot_id INTEGER NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
    farmer_id INTEGER NOT NULL REFERENCES farmers(id),
    receipt_number INTEGER NOT NULL,
    allocated_volume_kg REAL NOT NULL,
    num_bags INTEGER,
    gross_weight_kg REAL,
    delivered_date TEXT
);

CREATE TABLE IF NOT EXISTS incentives (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    incentive_date TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    lba_id INTEGER NOT NULL REFERENCES lbas(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (lba_id, key)
);

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    lba_id INTEGER NOT NULL REFERENCES lbas(id) ON DELETE CASCADE,
    uploaded_by INTEGER REFERENCES users(id),
    filename TEXT NOT NULL,
    s3_key TEXT NOT NULL,
    content_type TEXT,
    size_bytes INTEGER,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    lba_id INTEGER NOT NULL REFERENCES lbas(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_lba ON users(lba_id);
CREATE INDEX IF NOT EXISTS idx_farmers_lba ON farmers(lba_id);
CREATE INDEX IF NOT EXISTS idx_lots_lba ON lots(lba_id);
CREATE INDEX IF NOT EXISTS idx_alloc_farmer ON lot_allocations(farmer_id);
CREATE INDEX IF NOT EXISTS idx_alloc_lot ON lot_allocations(lot_id);
CREATE INDEX IF NOT EXISTS idx_incentives_farmer ON incentives(farmer_id);
CREATE INDEX IF NOT EXISTS idx_documents_lba ON documents(lba_id);
CREATE INDEX IF NOT EXISTS idx_audit_lba_created ON audit_log(lba_id, created_at DESC);
"""

# Changes made after the first deploy - kept separate from SCHEMA (which is
# only ever CREATE ... IF NOT EXISTS) so a column added to an existing,
# already-populated table doesn't need that table recreated.
MIGRATIONS = """
ALTER TABLE lots ADD COLUMN IF NOT EXISTS certification TEXT;
"""


def _resolve_dsn():
    global _cached_dsn
    if _cached_dsn:
        return _cached_dsn
    secret_arn = os.environ["DB_SECRET_ARN"]
    secret = json.loads(_secrets_client.get_secret_value(SecretId=secret_arn)["SecretString"])
    _cached_dsn = {
        "host": secret.get("host") or os.environ["DB_HOST"],
        "port": secret.get("port") or os.environ.get("DB_PORT", 5432),
        "dbname": os.environ.get("DB_NAME", "lba_production"),
        "user": secret["username"],
        "password": secret["password"],
    }
    return _cached_dsn


class _ConnWrapper:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        cur = self._conn.cursor()
        cur.execute(sql, params or ())
        return cur

    def commit(self):
        self._conn.commit()


@contextmanager
def get_conn():
    dsn = _resolve_dsn()
    conn = psycopg2.connect(cursor_factory=psycopg2.extras.RealDictCursor, **dsn)
    try:
        yield _ConnWrapper(conn)
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(SCHEMA)
        conn.execute(MIGRATIONS)


# Run once per cold start (module import is cached per execution environment,
# same as app.py calling db.init_db() once at startup) - idempotent, so safe
# on every cold start and the only schema-migration mechanism this backend
# needs, since Aurora has no public access to run a one-off script against.
init_db()


def get_setting(lba_id, key, default=None):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE lba_id=%s AND key=%s", (lba_id, key)
        ).fetchone()
        return row["value"] if row else default


def set_setting(lba_id, key, value):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings (lba_id, key, value) VALUES (%s, %s, %s) "
            "ON CONFLICT (lba_id, key) DO UPDATE SET value = excluded.value",
            (lba_id, key, value),
        )


CERTIFICATIONS = {
    "cocoa_horizons": "Cocoa Horizons",
    "rainforest_alliance": "Rainforest Alliance",
    "eudr": "EUDR",
}


def log_audit(conn, lba_id, user_id, action, entity_type=None, entity_id=None, details=None):
    """Writes one audit_log row on the SAME connection/transaction as the
    action it's recording, so the audit entry can never exist without the
    change it describes (or vice versa)."""
    conn.execute(
        "INSERT INTO audit_log (lba_id, user_id, action, entity_type, entity_id, details) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (lba_id, user_id, action, entity_type, str(entity_id) if entity_id is not None else None, details),
    )


def wipe_lba_data(lba_id):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM lot_allocations WHERE lot_id IN (SELECT id FROM lots WHERE lba_id=%s)",
            (lba_id,),
        )
        conn.execute("DELETE FROM lots WHERE lba_id=%s", (lba_id,))
        conn.execute(
            "DELETE FROM incentives WHERE farmer_id IN (SELECT id FROM farmers WHERE lba_id=%s)",
            (lba_id,),
        )
        conn.execute("DELETE FROM farmers WHERE lba_id=%s", (lba_id,))
