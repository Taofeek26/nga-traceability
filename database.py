"""Postgres access layer for the Nigeria LBA Level Traceability app.

Multi-tenant: every LBA (organisation) has one or more user accounts
(roles: admin / to / lba) and its own fully isolated farmers/lots/
incentives. There is no cross-LBA visibility anywhere - every query that
touches tenant data filters by lba_id.

Plain psycopg2 - no ORM - kept deliberately simple. Schema changes are
applied with ADD COLUMN IF NOT EXISTS / CREATE TABLE IF NOT EXISTS so
init_db() is safe to run against a database that already has data in it
(this app has no separate migration tool).
"""
import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Locally, put it in a .env file; on Vercel, "
        "add the Postgres integration and it will be set automatically."
    )

# Base schema - safe on a fresh database. Anything added after the first
# release lives in MIGRATIONS below instead of being edited in here, so
# that a database created by an older version of this file still ends up
# with the same final shape.
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

CREATE INDEX IF NOT EXISTS idx_users_lba ON users(lba_id);
CREATE INDEX IF NOT EXISTS idx_farmers_lba ON farmers(lba_id);
CREATE INDEX IF NOT EXISTS idx_lots_lba ON lots(lba_id);
CREATE INDEX IF NOT EXISTS idx_alloc_farmer ON lot_allocations(farmer_id);
CREATE INDEX IF NOT EXISTS idx_alloc_lot ON lot_allocations(lot_id);
CREATE INDEX IF NOT EXISTS idx_incentives_farmer ON incentives(farmer_id);
"""

# Changes made after the first release. Each is independently idempotent
# (IF NOT EXISTS / IF EXISTS everywhere) so running this against a brand
# new database (which already has the final shape from SCHEMA above) or
# an old one (which needs these applied) both end up identical.
MIGRATIONS = """
ALTER TABLE lbas ALTER COLUMN email DROP NOT NULL;
ALTER TABLE lbas ALTER COLUMN password_hash DROP NOT NULL;

ALTER TABLE farmers ADD COLUMN IF NOT EXISTS full_name TEXT;
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS farmer_uid TEXT;

-- first_name/surname only exist on pre-full_name databases, and are no
-- longer written to - drop their NOT NULL so new inserts (which only
-- set full_name) don't fail against a table that still has them.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'farmers' AND column_name = 'first_name'
    ) THEN
        ALTER TABLE farmers ALTER COLUMN first_name DROP NOT NULL;
        ALTER TABLE farmers ALTER COLUMN surname DROP NOT NULL;
    END IF;
END $$;

ALTER TABLE lots ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending';
ALTER TABLE lots ADD COLUMN IF NOT EXISTS vehicle_plate TEXT;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS driver_name TEXT;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS waybill_number TEXT;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS bags_declared INTEGER;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS moisture_pct REAL;
ALTER TABLE lots ADD COLUMN IF NOT EXISTS reviewed_by INTEGER REFERENCES users(id);
ALTER TABLE lots ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

ALTER TABLE lot_allocations ADD COLUMN IF NOT EXISTS num_bags INTEGER;
ALTER TABLE lot_allocations ADD COLUMN IF NOT EXISTS gross_weight_kg REAL;
ALTER TABLE lot_allocations ADD COLUMN IF NOT EXISTS delivered_date TEXT;
"""

# Data backfills - only touch rows that need it, safe to run every start.
BACKFILLS = [
    # Old deployments had first_name/surname instead of full_name.
    """
    UPDATE farmers SET full_name = TRIM(BOTH ' ' FROM (first_name || ' ' || surname))
    WHERE full_name IS NULL AND EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'farmers' AND column_name = 'first_name'
    );
    """,
    # Rows that somehow still have no full_name (fresh inserts between
    # the ALTER and the UPDATE above, or a first_name-less old row).
    "UPDATE farmers SET full_name = farmer_code WHERE full_name IS NULL;",
    # Old deployments authenticated the lbas row itself (email/password
    # directly on the organisation). Give every such org an admin user
    # with the same credentials so existing logins keep working.
    """
    INSERT INTO users (lba_id, name, email, password_hash, role)
    SELECT l.id, l.name, l.email, l.password_hash, 'admin'
    FROM lbas l
    WHERE l.email IS NOT NULL
      AND l.password_hash IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM users u WHERE u.lba_id = l.id);
    """,
    # Allocations recorded before per-farmer delivered_date existed - fall
    # back to their lot's own date rather than leaving it NULL.
    """
    UPDATE lot_allocations a SET delivered_date = l.lot_date
    FROM lots l
    WHERE a.lot_id = l.id AND a.delivered_date IS NULL;
    """,
]


class _ConnWrapper:
    """Gives the psycopg2 connection a sqlite3-style .execute() so call
    sites can do conn.execute(sql, params).fetchone()/.fetchall(), same
    shape as the original SQLite version of this app."""

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
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield _ConnWrapper(conn)
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(SCHEMA)
        conn.execute(MIGRATIONS)
        for stmt in BACKFILLS:
            conn.execute(stmt)
        conn.execute("ALTER TABLE farmers ALTER COLUMN full_name SET NOT NULL")
        # Per-lba settings are created lazily (see get_setting's `default`
        # argument) rather than pre-seeded here.


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


def wipe_lba_data(lba_id):
    """Full reset for one LBA: their farmers, lots, allocations, incentives.
    Other LBAs' data, this LBA's user accounts, are untouched."""
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
