# Page blueprints

Each page below has a reference template in `templates/pages/`. The **context**
column lists the variables the FastAPI route passes in `app.py` — templates must
use these and nothing else (plus `request` and `lba_name`, added by `render()`).

## App shell (`base.html`)

```
┌──────────┬─────────────────────────────────────────────┐
│ Sidebar  │ Topbar: [☰ mobile] Home › Section › Page    │
│ brand    ├─────────────────────────────────────────────┤
│ OVERVIEW │ Page header: eyebrow / title / desc  [CTA]  │
│ TRACE…   │ Alerts                                      │
│ ADMIN    │ Stats row                                   │
│          │ Cards / tables / forms                      │
│ account  │                                             │
└──────────┴─────────────────────────────────────────────┘
```
Nav groups: Overview (Dashboard) · Traceability (New Lot, Lot History, Farmers)
· Administration (Master Data, Settings).

---

### Dashboard — `dashboard.html` — `/`
Context: `n_farmers, n_active, potential, delivered, n_lots, recent_lots, near_limit`
1. Page header (eyebrow = LBA name) + actions: *Update master data* (secondary), *New lot* (accent).
2. Stats: Farmers on file · Potential volume · Delivered so far (with % used) · Lots recorded (highlight).
3. Get-started steps card — only when `n_lots == 0`.
4. Two-column grid: Recent lots table (left) · Near-limit list with progress bars (right aside).

### Farmers — `farmers.html` — `/farmers`
Context: `farmers, q`
1. Page header + *Import from Excel*.
2. Card: search toolbar (GET `q`) → table: farmer (avatar, name, code) · community · potential · delivered · remaining · quota meter · status badge.
3. Empty states for "no match" vs "no farmers yet".

### Farmer detail — `farmer_detail.html` — `/farmers/{code}`
Context: `f, delivered, remaining, premium_rate, premium_accrued, other_incentives, total_entitlement, incentives, deliveries, msg`
1. Breadcrumbs Home › Farmers › Name. Profile header: XL gold avatar, name, code tag, community, status; *Mark inactive / Reactivate* (POST toggle-active).
2. Stats: potential · delivered · remaining · plots (+ ha).
3. Quota meter card.
4. Main/aside grid — main: Entitlements card (summary strip + incentive form + incentive table), Delivery history card; aside: Farmer details `dl`.

### Lot history — `lots.html` — `/lots`
Context: `lots`
Page header + *New lot* (accent) → card with table: date/lot # · receipt range tag · farmers · volume · note · View.

### New lot — `new_lot.html` — `/lots/new` (narrow)
Context: `today, n_eligible, error`
Alert (error / warning when `n_eligible == 0` / info with eligible count) → form card with three `.form-section`s: Delivery (date, volume kg) · Receipt booklet (range pair) · Reference (note). Footer: Cancel (ghost) + *Generate farmer list* (primary, disabled when none eligible).
Field names: `lot_date, total_volume_kg, receipt_start, receipt_end, note`.

### Lot result — `lot_result.html` — `/lots/{id}`
Context: `lot, rows`
Breadcrumbs › Lot History › Lot #. Page header (eyebrow = date, desc = note) + *Record another*, *Export farmer list* → success alert → summary strip (date, receipts, farmers, total) → farmer list table with `tfoot` total → sticky action bar.

### Master data — `upload.html` — `/upload` (narrow)
Context: `msg, error`
Upload card: header with *Template* download, dropzone (`name="file"`), required/optional column tags, footer *Upload*. Danger zone: type `CLEAR` (`name="confirm"`) → POST `/data/clear`.

### Settings — `settings.html` — `/settings` (narrow)
Context: `rate, msg`
Form card with one `.form-section`: Premium rate (`name="premium_rate_per_kg"`, ₦ … / kg add-ons). Footer *Save changes*.

### Login / Signup — `login.html`, `signup.html` (extend `auth_base.html`)
Context: login `error, msg` · signup `error`
Split screen: dark brown brand panel (headline, three feature checks, gold glow) + form panel. Below 900 px only the form shows, with a compact brand mark.
Field names — login: `email, password` · signup: `name, email, password, confirm_password`.
