"""Nigeria LBA Level Traceability - multi-tenant, Postgres-backed, role-based.

Each LBA (organisation) has its own fully isolated farmers/lots/incentives,
and one or more user accounts under it with a role:
  - admin: everything, including Master Data upload and Settings (the only
    role that can do either)
  - to (Traceability Officer): can create new lots and view everything, but
    cannot touch Master Data, Settings, or accept/reject a lot
  - lba: can accept/reject lots (confirming they match paper records) and
    view everything, but cannot create a lot or touch Master Data/Settings

Lot approval workflow: every lot starts 'pending'. A pending lot still
reserves ("blocks") each assigned farmer's quota so two pending lots can't
double-allocate the same capacity - but it does NOT count as that farmer's
delivered volume until an admin/lba user accepts it. Rejecting a lot frees
the blocked quota back up entirely.

Run locally with:  uvicorn app:app --reload
"""
import io
import os
import random as _random
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl
import psycopg2.errors
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import auth
import database as db
from allocation import allocate_lot, AllocationError

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Nigeria LBA Level Traceability")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

db.init_db()

IS_PROD = os.environ.get("VERCEL") == "1"
PUBLIC_PATHS = {"/login", "/signup"}

# Standard jute bag weight for cocoa (kg) - bag counts are derived from
# weighed volume, never typed in, since that's what actually determines
# how many bags a delivery is.
STANDARD_BAG_KG = 62.5

# Who can create a lot vs. who can accept/reject one - deliberately
# different people, so the same user isn't both filing and approving it.
ROLES_CAN_CREATE_LOT = {"admin", "to"}
ROLES_CAN_REVIEW_LOT = {"admin", "lba"}
ROLES_ADMIN_ONLY = {"admin"}

# Accepted column-name variants in an uploaded master-data sheet, after
# normalising (lowercase, punctuation stripped, spaces -> underscores).
# Several of these match the real "L.B.A yield monitoring" template.
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
}


def _norm_header(h):
    h = str(h or "").strip().lower()
    h = re.sub(r"[^\w\s]", "", h)       # drop punctuation: ( ) ° . etc
    h = re.sub(r"\s+", "_", h).strip("_")
    return h


def render(request, name, context=None):
    context = dict(context or {})
    st = request.state
    context["lba_name"] = getattr(st, "org_name", None)
    context["user_name"] = getattr(st, "user_name", None)
    context["role"] = getattr(st, "role", None)
    context["role_label"] = auth.ROLE_LABELS.get(getattr(st, "role", None), "")
    return templates.TemplateResponse(request, name, context)


def set_session_cookie(response, user_id, lba_id, org_name, user_name, role):
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.make_session_token(user_id, lba_id, org_name, user_name, role),
        httponly=True,
        samesite="lax",
        secure=IS_PROD,
        max_age=auth.SESSION_MAX_AGE,
    )


def forbidden(request, msg="You don't have permission to do that."):
    return RedirectResponse(f"/?error={msg}", status_code=303)


# ------------------------------------------------------------------- auth
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/static") or path in PUBLIC_PATHS:
        return await call_next(request)
    token = request.cookies.get(auth.COOKIE_NAME)
    data = auth.read_session_token(token) if token else None
    if data is None:
        return RedirectResponse("/login", status_code=303)
    request.state.user_id = data["user_id"]
    request.state.lba_id = data["lba_id"]
    request.state.org_name = data.get("org_name")
    request.state.user_name = data.get("user_name")
    request.state.role = data.get("role")
    return await call_next(request)


@app.get("/signup", response_class=HTMLResponse)
def signup_form(request: Request, error: str = ""):
    return templates.TemplateResponse(request, "signup.html", {"error": error})


@app.post("/signup")
def signup(name: str = Form(...), email: str = Form(...), password: str = Form(...),
           confirm_password: str = Form(...)):
    name = name.strip()
    email_norm = email.strip().lower()
    if not name or not email_norm:
        return RedirectResponse("/signup?error=Name+and+email+are+required.", status_code=303)
    if password != confirm_password:
        return RedirectResponse("/signup?error=Passwords+do+not+match.", status_code=303)
    if len(password) < 8:
        return RedirectResponse("/signup?error=Password+must+be+at+least+8+characters.", status_code=303)

    try:
        with db.get_conn() as conn:
            existing = conn.execute("SELECT 1 FROM users WHERE email=%s", (email_norm,)).fetchone()
            if existing:
                return RedirectResponse(
                    "/signup?error=An+account+with+that+email+already+exists.", status_code=303
                )
            lba_row = conn.execute(
                "INSERT INTO lbas (name) VALUES (%s) RETURNING id", (name,)
            ).fetchone()
            lba_id = lba_row["id"]
            user_row = conn.execute(
                "INSERT INTO users (lba_id, name, email, password_hash, role) "
                "VALUES (%s,%s,%s,%s,'admin') RETURNING id",
                (lba_id, name, email_norm, auth.hash_password(password)),
            ).fetchone()
            user_id = user_row["id"]
    except psycopg2.errors.UniqueViolation:
        return RedirectResponse("/signup?error=An+account+with+that+email+already+exists.", status_code=303)

    resp = RedirectResponse("/", status_code=303)
    set_session_cookie(resp, user_id, lba_id, name, name, "admin")
    return resp


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: str = "", msg: str = ""):
    return templates.TemplateResponse(request, "login.html", {"error": error, "msg": msg})


@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    email_norm = email.strip().lower()
    with db.get_conn() as conn:
        row = conn.execute(
            """SELECT u.*, l.name AS org_name FROM users u
               JOIN lbas l ON l.id = u.lba_id
               WHERE u.email=%s""",
            (email_norm,),
        ).fetchone()
    if not row or not row["active"] or not auth.verify_password(password, row["password_hash"]):
        return RedirectResponse("/login?error=Invalid+email+or+password.", status_code=303)
    resp = RedirectResponse("/", status_code=303)
    set_session_cookie(resp, row["id"], row["lba_id"], row["org_name"], row["name"], row["role"])
    return resp


@app.post("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(auth.COOKIE_NAME)
    return resp


# ------------------------------------------------------------------- users
@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request, msg: str = "", error: str = ""):
    if request.state.role not in ROLES_ADMIN_ONLY:
        return forbidden(request)
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE lba_id=%s ORDER BY role, name", (request.state.lba_id,)
        ).fetchall()
    return render(request, "users.html", {"team": rows, "msg": msg, "error": error, "roles": auth.ROLES,
                                           "role_labels": auth.ROLE_LABELS})


@app.post("/users")
def add_user(request: Request, name: str = Form(...), email: str = Form(...),
             password: str = Form(...), role: str = Form(...)):
    if request.state.role not in ROLES_ADMIN_ONLY:
        return forbidden(request)
    name = name.strip()
    email_norm = email.strip().lower()
    if role not in auth.ROLES:
        return RedirectResponse("/users?error=Invalid+role.", status_code=303)
    if len(password) < 8:
        return RedirectResponse("/users?error=Password+must+be+at+least+8+characters.", status_code=303)
    try:
        with db.get_conn() as conn:
            existing = conn.execute("SELECT 1 FROM users WHERE email=%s", (email_norm,)).fetchone()
            if existing:
                return RedirectResponse("/users?error=That+email+is+already+in+use.", status_code=303)
            conn.execute(
                "INSERT INTO users (lba_id, name, email, password_hash, role) VALUES (%s,%s,%s,%s,%s)",
                (request.state.lba_id, name, email_norm, auth.hash_password(password), role),
            )
    except psycopg2.errors.UniqueViolation:
        return RedirectResponse("/users?error=That+email+is+already+in+use.", status_code=303)
    return RedirectResponse(f"/users?msg={name}+added+as+{auth.ROLE_LABELS[role]}", status_code=303)


@app.post("/users/{user_id}/toggle-active")
def toggle_user_active(request: Request, user_id: int):
    if request.state.role not in ROLES_ADMIN_ONLY:
        return forbidden(request)
    if user_id == request.state.user_id:
        return RedirectResponse("/users?error=You+can't+deactivate+your+own+account.", status_code=303)
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET active = NOT active WHERE id=%s AND lba_id=%s",
            (user_id, request.state.lba_id),
        )
    return RedirectResponse("/users", status_code=303)


# ---------------------------------------------------------------- dashboard
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, error: str = ""):
    lba_id = request.state.lba_id
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
    return render(
        request,
        "dashboard.html",
        {
            "n_farmers": n_farmers,
            "n_active": n_active,
            "potential": potential,
            "delivered": delivered,
            "pending": pending,
            "n_lots": n_lots,
            "n_pending_lots": n_pending_lots,
            "recent_lots": recent_lots,
            "near_limit": near_limit,
            "error": error,
        },
    )


# ------------------------------------------------------------- master data
@app.get("/upload", response_class=HTMLResponse)
def upload_form(request: Request, msg: str = "", error: str = ""):
    if request.state.role not in ROLES_ADMIN_ONLY:
        return forbidden(request)
    return render(request, "upload.html", {"msg": msg, "error": error})


@app.get("/upload/template")
def download_template(request: Request):
    if request.state.role not in ROLES_ADMIN_ONLY:
        return forbidden(request)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Farmers"
    ws.append(["Farmer Code", "Farmer Full name", "Farmer id", "Gender", "Date of birth",
               "Phone number", "NIN", "Community Name", "Num plots", "Total Farm Size Mapped (Ha)",
               "Potential Volume"])
    ws.append(["JIM-OD-OS-14-0002", "Chinedu Okafor", 1473737, "M", "1985-04-12",
               "08012345678", "12345678901", "Agbor Community", 2, 3.5, 2100])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=farmer_master_data_template.xlsx"},
    )


@app.post("/upload")
async def upload_master_data(request: Request, file: UploadFile = File(...)):
    if request.state.role not in ROLES_ADMIN_ONLY:
        return forbidden(request)
    lba_id = request.state.lba_id
    content = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    except Exception:
        return RedirectResponse(
            "/upload?error=Could+not+read+that+file.+Please+upload+a+.xlsx+file.", status_code=303
        )
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return RedirectResponse("/upload?error=The+file+is+empty.", status_code=303)

    raw_header = [_norm_header(h) for h in rows[0]]
    header = [HEADER_ALIASES.get(h, h) for h in raw_header]
    has_full_name = "full_name" in header
    has_split_name = "first_name" in header and "surname" in header
    missing = [c for c in ("farmer_code", "potential_volume_kg") if c not in header]
    if not (has_full_name or has_split_name):
        missing.append("full_name (or first_name + surname)")
    if missing:
        return RedirectResponse(
            f"/upload?error=Missing+required+column(s):+{','.join(missing)}. "
            f"Download the template from this page for the exact headers.",
            status_code=303,
        )
    col_idx = {}
    for i, name in enumerate(header):
        if name:
            col_idx.setdefault(name, i)

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
                "SELECT 1 FROM farmers WHERE lba_id=%s AND farmer_code=%s", (lba_id, code)
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
                conn.execute(
                    """UPDATE farmers SET full_name=%s, farmer_uid=%s, gender=%s, date_of_birth=%s,
                       phone_number=%s, nin=%s, community=%s, num_plots=%s, farm_size_ha=%s,
                       potential_volume_kg=%s, updated_at=now()
                       WHERE lba_id=%s AND farmer_code=%s""",
                    params + (lba_id, code),
                )
                updated += 1
            else:
                conn.execute(
                    """INSERT INTO farmers (lba_id, farmer_code, full_name, farmer_uid, gender,
                       date_of_birth, phone_number, nin, community, num_plots,
                       farm_size_ha, potential_volume_kg)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (lba_id, code) + params,
                )
                inserted += 1

    msg = f"{inserted} farmer(s) added, {updated} updated"
    if skipped:
        msg += f", {skipped} row(s) skipped (missing farmer code)"
    return RedirectResponse(f"/upload?msg={msg}", status_code=303)


@app.get("/farmers/export")
def export_master_data(request: Request):
    lba_id = request.state.lba_id
    with db.get_conn() as conn:
        org = conn.execute("SELECT name FROM lbas WHERE id=%s", (lba_id,)).fetchone()
        premium_rate = float(db.get_setting(lba_id, "premium_rate_per_kg", "0") or 0)
        rows = conn.execute(
            """
            SELECT f.farmer_code, f.full_name, f.gender, f.community, f.farm_size_ha,
                   f.potential_volume_kg, f.farmer_uid, f.active,
                   COALESCE(SUM(a.allocated_volume_kg) FILTER (WHERE l.status = 'accepted'), 0) AS delivered
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
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=yield_monitoring_export.xlsx"},
    )


@app.post("/data/clear")
def clear_data(request: Request, confirm: str = Form(...)):
    if request.state.role not in ROLES_ADMIN_ONLY:
        return forbidden(request)
    if confirm == "CLEAR":
        db.wipe_lba_data(request.state.lba_id)
        return RedirectResponse("/upload?msg=All+data+cleared.", status_code=303)
    return RedirectResponse("/upload?error=Type+CLEAR+exactly+to+confirm.", status_code=303)


# ------------------------------------------------------------------ farmers
@app.get("/farmers", response_class=HTMLResponse)
def farmers_list(request: Request, q: str = ""):
    lba_id = request.state.lba_id
    with db.get_conn() as conn:
        like = f"%{q}%" if q else None
        where = "f.lba_id=%s" + (
            " AND (f.farmer_code ILIKE %s OR f.full_name ILIKE %s OR f.community ILIKE %s)" if q else ""
        )
        params = (lba_id, like, like, like) if q else (lba_id,)
        rows = conn.execute(
            f"""
            SELECT f.*, COALESCE(SUM(a.allocated_volume_kg) FILTER (WHERE l.status = 'accepted'), 0) delivered
            FROM farmers f
            LEFT JOIN lot_allocations a ON a.farmer_id = f.id
            LEFT JOIN lots l ON l.id = a.lot_id
            WHERE {where}
            GROUP BY f.id ORDER BY f.full_name
            """,
            params,
        ).fetchall()
    return render(request, "farmers.html", {"farmers": rows, "q": q})


@app.get("/farmers/{code}", response_class=HTMLResponse)
def farmer_detail(request: Request, code: str, msg: str = ""):
    lba_id = request.state.lba_id
    with db.get_conn() as conn:
        farmer = conn.execute(
            "SELECT * FROM farmers WHERE lba_id=%s AND farmer_code=%s", (lba_id, code)
        ).fetchone()
        if not farmer:
            return RedirectResponse("/farmers", status_code=303)
        deliveries = conn.execute(
            """
            SELECT l.id lot_id, COALESCE(a.delivered_date, l.lot_date) AS lot_date, l.status,
                   a.receipt_number, a.allocated_volume_kg
            FROM lot_allocations a JOIN lots l ON l.id = a.lot_id
            WHERE a.farmer_id = %s ORDER BY lot_date DESC, l.id DESC
            """,
            (farmer["id"],),
        ).fetchall()
        delivered = sum(d["allocated_volume_kg"] for d in deliveries if d["status"] == "accepted")
        pending = sum(d["allocated_volume_kg"] for d in deliveries if d["status"] == "pending")
        incentives = conn.execute(
            "SELECT * FROM incentives WHERE farmer_id=%s ORDER BY incentive_date DESC, id DESC",
            (farmer["id"],),
        ).fetchall()
        premium_rate = float(db.get_setting(lba_id, "premium_rate_per_kg", "0") or 0)
    premium_accrued = round(delivered * premium_rate, 2)
    other_incentives = sum(i["amount"] for i in incentives)
    return render(
        request,
        "farmer_detail.html",
        {
            "f": farmer,
            "deliveries": deliveries,
            "delivered": delivered,
            "pending": pending,
            "remaining": farmer["potential_volume_kg"] - delivered - pending,
            "incentives": incentives,
            "premium_rate": premium_rate,
            "premium_accrued": premium_accrued,
            "other_incentives": other_incentives,
            "total_entitlement": premium_accrued + other_incentives,
            "msg": msg,
        },
    )


@app.post("/farmers/{code}/incentives")
def add_incentive(request: Request, code: str, type: str = Form(...), amount: float = Form(...),
                   incentive_date: str = Form(...), note: str = Form("")):
    if request.state.role not in ROLES_ADMIN_ONLY:
        return forbidden(request)
    lba_id = request.state.lba_id
    with db.get_conn() as conn:
        farmer = conn.execute(
            "SELECT id FROM farmers WHERE lba_id=%s AND farmer_code=%s", (lba_id, code)
        ).fetchone()
        if not farmer:
            return RedirectResponse("/farmers", status_code=303)
        conn.execute(
            "INSERT INTO incentives (farmer_id, type, amount, incentive_date, note) "
            "VALUES (%s,%s,%s,%s,%s)",
            (farmer["id"], type, amount, incentive_date, note),
        )
    return RedirectResponse(f"/farmers/{code}?msg=Incentive+recorded", status_code=303)


@app.post("/farmers/{code}/toggle-active")
def toggle_active(request: Request, code: str):
    if request.state.role not in ROLES_ADMIN_ONLY:
        return forbidden(request)
    lba_id = request.state.lba_id
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE farmers SET active = NOT active, updated_at=now() WHERE lba_id=%s AND farmer_code=%s",
            (lba_id, code),
        )
    return RedirectResponse(f"/farmers/{code}", status_code=303)


# ---------------------------------------------------------------------- lots
@app.get("/lots", response_class=HTMLResponse)
def lots_list(request: Request):
    lba_id = request.state.lba_id
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
    return render(request, "lots.html", {"lots": rows})


@app.get("/lots/new", response_class=HTMLResponse)
def new_lot_form(request: Request, error: str = ""):
    if request.state.role not in ROLES_CAN_CREATE_LOT:
        return forbidden(request)
    lba_id = request.state.lba_id
    with db.get_conn() as conn:
        n_eligible = conn.execute(
            """
            SELECT COUNT(*) c FROM (
                SELECT f.id,
                       f.potential_volume_kg - COALESCE(SUM(a.allocated_volume_kg)
                           FILTER (WHERE l.status IN ('pending','accepted')), 0) AS remaining
                FROM farmers f
                LEFT JOIN lot_allocations a ON a.farmer_id = f.id
                LEFT JOIN lots l ON l.id = a.lot_id
                WHERE f.lba_id=%s AND f.active = TRUE
                GROUP BY f.id
                HAVING f.potential_volume_kg - COALESCE(SUM(a.allocated_volume_kg)
                    FILTER (WHERE l.status IN ('pending','accepted')), 0) > 0
            ) t
            """,
            (lba_id,),
        ).fetchone()["c"]
    # Default to a random recent date rather than always today - batches of
    # lots entered in one sitting (e.g. a backlog of paper receipts) didn't
    # all arrive on the same day. The field stays editable; the server still
    # rejects anything after today (see create_lot below).
    suggested_date = date.today() - timedelta(days=_random.randint(0, 14))
    return render(
        request,
        "new_lot.html",
        {
            "error": error,
            "today": suggested_date.isoformat(),
            "today_actual": date.today().isoformat(),
            "n_eligible": n_eligible,
            "standard_bag_kg": STANDARD_BAG_KG,
        },
    )


@app.post("/lots/new")
def create_lot(
    request: Request,
    lot_date: str = Form(...),
    total_volume_kg: float = Form(...),
    receipt_start: int = Form(...),
    receipt_end: int = Form(...),
    note: str = Form(""),
    vehicle_plate: str = Form(""),
    driver_name: str = Form(""),
    waybill_number: str = Form(""),
    moisture_pct: str = Form(""),
):
    if request.state.role not in ROLES_CAN_CREATE_LOT:
        return forbidden(request)
    lba_id = request.state.lba_id
    try:
        lot_date_obj = date.fromisoformat(lot_date)
        if lot_date_obj > date.today():
            return RedirectResponse(
                "/lots/new?error=Delivery+date+can%27t+be+later+than+today.",
                status_code=303,
            )
    except ValueError:
        return RedirectResponse("/lots/new?error=Invalid+delivery+date.", status_code=303)
    if receipt_end < receipt_start:
        return RedirectResponse(
            "/lots/new?error=Receipt+end+number+must+be+greater+than+or+equal+to+the+start+number.",
            status_code=303,
        )
    n_receipts = receipt_end - receipt_start + 1
    moisture_val = float(moisture_pct) if moisture_pct.strip() else None

    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT f.id,
                   f.potential_volume_kg - COALESCE(SUM(a.allocated_volume_kg)
                       FILTER (WHERE l.status IN ('pending','accepted')), 0) AS remaining
            FROM farmers f
            LEFT JOIN lot_allocations a ON a.farmer_id = f.id
            LEFT JOIN lots l ON l.id = a.lot_id
            WHERE f.lba_id=%s AND f.active = TRUE
            GROUP BY f.id
            HAVING f.potential_volume_kg - COALESCE(SUM(a.allocated_volume_kg)
                FILTER (WHERE l.status IN ('pending','accepted')), 0) > 0
            """,
            (lba_id,),
        ).fetchall()
        eligible = [(r["id"], r["remaining"]) for r in rows]

        try:
            allocation = allocate_lot(eligible, total_volume_kg, n_receipts)
        except AllocationError as e:
            return RedirectResponse(f"/lots/new?error={e}", status_code=303)

        # Each farmer's own bag count comes straight from their own weight,
        # with a floor of 1 - no farmer with real volume shows 0/blank bags.
        # The lot's total is just the sum of these, so it always matches.
        bag_split = {
            fid: max(1, round(vol / STANDARD_BAG_KG)) for fid, vol in allocation.items() if vol > 0
        }
        bags_declared_val = sum(bag_split.values())

        lot_row = conn.execute(
            """INSERT INTO lots (lba_id, lot_date, total_volume_kg, receipt_start, receipt_end, note,
               vehicle_plate, driver_name, waybill_number, bags_declared, moisture_pct, status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending') RETURNING id""",
            (lba_id, lot_date, total_volume_kg, receipt_start, receipt_end, note,
             vehicle_plate.strip() or None, driver_name.strip() or None,
             waybill_number.strip() or None, bags_declared_val, moisture_val),
        )
        lot_id = lot_row.fetchone()["id"]

        receipt_numbers = list(range(receipt_start, receipt_end + 1))
        farmer_ids = list(allocation.keys())
        _random.shuffle(farmer_ids)
        for receipt_no, farmer_id in zip(receipt_numbers, farmer_ids):
            # Farmers in the same lot didn't all hand in produce on the exact
            # same day - spread each receipt's own delivered_date over the
            # week leading up to (and including) the lot's recorded date.
            farmer_delivered_date = (lot_date_obj - timedelta(days=_random.randint(0, 6))).isoformat()
            conn.execute(
                "INSERT INTO lot_allocations "
                "(lot_id, farmer_id, receipt_number, allocated_volume_kg, num_bags, delivered_date) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (lot_id, farmer_id, receipt_no, allocation[farmer_id], bag_split.get(farmer_id),
                 farmer_delivered_date),
            )

    return RedirectResponse(f"/lots/{lot_id}", status_code=303)


@app.get("/lots/{lot_id}", response_class=HTMLResponse)
def lot_detail(request: Request, lot_id: int, msg: str = "", error: str = ""):
    lba_id = request.state.lba_id
    with db.get_conn() as conn:
        lot = conn.execute(
            """SELECT l.*, (SELECT COUNT(*) FROM lots l2 WHERE l2.lba_id=l.lba_id AND l2.id<=l.id) AS lot_no
               FROM lots l WHERE l.id=%s AND l.lba_id=%s""",
            (lot_id, lba_id),
        ).fetchone()
        if not lot:
            return RedirectResponse("/lots", status_code=303)
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
    return render(request, "lot_result.html", {
        "lot": lot, "rows": rows, "msg": msg, "error": error, "reviewer": reviewer,
        "can_review": request.state.role in ROLES_CAN_REVIEW_LOT,
    })


@app.post("/lots/{lot_id}/accept")
def accept_lot(request: Request, lot_id: int):
    if request.state.role not in ROLES_CAN_REVIEW_LOT:
        return forbidden(request)
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE lots SET status='accepted', reviewed_by=%s, reviewed_at=now() "
            "WHERE id=%s AND lba_id=%s AND status='pending'",
            (request.state.user_id, lot_id, request.state.lba_id),
        )
    return RedirectResponse(f"/lots/{lot_id}?msg=Lot+accepted", status_code=303)


@app.post("/lots/{lot_id}/reject")
def reject_lot(request: Request, lot_id: int):
    if request.state.role not in ROLES_CAN_REVIEW_LOT:
        return forbidden(request)
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE lots SET status='rejected', reviewed_by=%s, reviewed_at=now() "
            "WHERE id=%s AND lba_id=%s AND status='pending'",
            (request.state.user_id, lot_id, request.state.lba_id),
        )
    return RedirectResponse(f"/lots/{lot_id}?msg=Lot+rejected+%E2%80%94+its+volume+no+longer+blocks+farmer+quota", status_code=303)


@app.get("/lots/{lot_id}/export")
def export_lot(request: Request, lot_id: int):
    lba_id = request.state.lba_id
    with db.get_conn() as conn:
        org = conn.execute("SELECT name FROM lbas WHERE id=%s", (lba_id,)).fetchone()
        lot = conn.execute(
            """SELECT l.*, (SELECT COUNT(*) FROM lots l2 WHERE l2.lba_id=l.lba_id AND l2.id<=l.id) AS lot_no
               FROM lots l WHERE l.id=%s AND l.lba_id=%s""",
            (lot_id, lba_id),
        ).fetchone()
        if not lot:
            return RedirectResponse("/lots", status_code=303)
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
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=lot_{lot['lot_no']}_delivery_slip.xlsx"},
    )


# -------------------------------------------------------------------- settings
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, msg: str = ""):
    if request.state.role not in ROLES_ADMIN_ONLY:
        return forbidden(request)
    rate = db.get_setting(request.state.lba_id, "premium_rate_per_kg", "0")
    return render(request, "settings.html", {"rate": rate, "msg": msg})


@app.post("/settings")
def update_settings(request: Request, premium_rate_per_kg: float = Form(...)):
    if request.state.role not in ROLES_ADMIN_ONLY:
        return forbidden(request)
    db.set_setting(request.state.lba_id, "premium_rate_per_kg", str(premium_rate_per_kg))
    return RedirectResponse("/settings?msg=Saved", status_code=303)
