# Nigeria LBA Level Traceability

A tool for LBAs to solve one specific problem: a broker-sourced lot arrives with
only a total weight and a receipt range — nobody recorded which registered farmer
supplied how much. This app generates a plausible, quota-respecting farmer list
for that lot automatically, and keeps a running picture of how much of each
farmer's potential volume has been used.

**Multi-tenant**: any number of LBAs can use the same deployed app. Each one signs
up for its own account and only ever sees its own farmers, lots and data — there
is no shared visibility between LBAs anywhere in the system.

## Does data survive between visits?

Yes. Data lives in a Postgres database, not in the browser or on any one laptop.
Whoever is logged in as a given LBA sees exactly what that LBA uploaded and
recorded last time, every time they log back in — from any device, any time.
Nothing is lost when a browser tab closes, a laptop restarts, or the app
redeploys. The only way data for an LBA disappears is if someone logged into
that LBA's account deliberately uses **Master Data → Clear all data** (which
requires typing `CLEAR` to confirm).

## What it does

- **Accounts**: each LBA registers with a name, email and password. Logging in
  only ever shows that LBA's own data.
- **Master data**: upload/refresh your farmer register from Excel (matched and
  updated by Farmer Code, scoped to your account — re-uploading never deletes
  anyone and never touches another LBA's farmers).
- **New lot**: enter the lot's total volume and the receipt booklet range you
  used (e.g. 1001–1030 = 30 receipts). The app randomly picks that many active
  farmers (from your own register) with remaining quota and splits the volume
  across them so nobody's running total ever exceeds their potential volume —
  then assigns the receipt numbers.
- **Farmer list export**: the generated list (receipt no., farmer, volume)
  exports straight to Excel — this is your Traceability Report / farmer list
  for the lot.
- **Farmer detail page**: potential volume, delivered so far, remaining quota,
  number of plots, farm size, full delivery history, and entitlements (premium
  accrued + manually logged incentives like bonuses or training stipends).
- **Clear all data**: wipes everything *for your account only* to start a fresh
  season. Type-to-confirm, no backup — use with care.

## How the allocation works

Given a lot volume and a number of receipts (`end − start + 1`):
1. Pulls every active farmer **belonging to the logged-in LBA** whose
   `potential_volume_kg − delivered_so_far > 0`.
2. Randomly samples that many farmers, retrying if the sample can't cover the
   lot, falling back to the highest-capacity farmers if needed.
3. Randomly splits the lot volume across them (genuinely randomised
   proportions, not an even split), clipping anyone who'd exceed their
   remaining quota and redistributing the excess to farmers who still have
   room, until the full volume is placed.
4. Shuffles farmer order and assigns receipt numbers sequentially.

If there genuinely isn't enough combined remaining quota among active farmers
to cover the lot, it says so plainly instead of silently over-allocating
anyone.

## Running it locally

Requires a Postgres database (see below for the quickest way to get one).

```bash
cd lba-traceability-app
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then fill in DATABASE_URL and SECRET_KEY
uvicorn app:app --reload
```

Open **http://127.0.0.1:8000**, click "Register your LBA" to create the first
account, and go from there.

### Getting a local/dev Postgres database

Easiest: create a free [Neon](https://neon.tech) or
[Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres) database and
paste its connection string into `.env` as `DATABASE_URL`. Or, if you have
Postgres installed locally (e.g. via Homebrew: `brew install postgresql@14`):

```bash
brew services start postgresql@14
createdb lba_traceability_dev
# DATABASE_URL=postgresql://<your-mac-username>@localhost:5432/lba_traceability_dev
```

`SECRET_KEY` can be any random string — generate one with:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Deploying to Vercel

**Already deployed and live at: https://nigeria-lba-traceability.vercel.app**

This used Vercel's native FastAPI detection — `api/index.py` re-exports the
app from the project root, and Vercel routes all paths to it automatically.
No `vercel.json` is needed (an earlier version of this project had one with a
manual catch-all rewrite; that actively broke routing, because Vercel's
backend-framework detection rewrites the *path the app sees*, not just where
the request is sent — `/login` ended up looking like `/api/index.py` to
FastAPI's own router, which broke the login-page allowlist and caused a
redirect loop. Removing `vercel.json` entirely and letting Vercel's framework
detection handle routing fixed it.)

To redeploy after a code change, from inside `lba-traceability-app/`:
```bash
vercel --prod
```

### Setting this up from scratch on a different account

1. **Install/locate the Vercel CLI** and log in:
   ```bash
   npm install -g vercel   # or use npx vercel <command> with no install
   vercel login
   ```

2. **Link the project:**
   ```bash
   vercel link --yes --project your-project-name
   ```

3. **Provision Postgres** (Neon, via Vercel's marketplace) and connect it:
   ```bash
   vercel integration accept-terms neon --yes   # one-time, first project only
   vercel install neon --name your-project-db
   ```
   This automatically sets `DATABASE_URL` (and several `POSTGRES_*` aliases)
   as environment variables on the project — `database.py` reads
   `DATABASE_URL` or `POSTGRES_URL`, so no manual wiring is needed.

4. **Set `SECRET_KEY`** (required — without it, sessions can't be signed and
   nobody can log in):
   ```bash
   SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
   vercel env add SECRET_KEY production --value "$SECRET" --sensitive --yes
   vercel env add SECRET_KEY preview --value "$SECRET" --sensitive --yes
   vercel env add SECRET_KEY development --value "$SECRET" --sensitive --yes
   ```

5. **Deploy:**
   ```bash
   vercel --prod --yes
   ```
   The first request after deploy runs `database.init_db()`, which creates
   all tables automatically (`CREATE TABLE IF NOT EXISTS`) — no separate
   migration step, and re-deploys never wipe or duplicate existing data.

7. Share the resulting `https://your-project.vercel.app` URL with any LBA that
   needs access. Each one clicks "Register your LBA" and creates its own
   account — you don't need to create accounts for them.

### Re-deploying after a code change

Just run `vercel --prod` again from the project folder. The schema uses
`CREATE TABLE IF NOT EXISTS`, so re-deploys never wipe or duplicate existing
data.

## Master data columns

Required: `farmer_code`, `first_name`, `surname`, `potential_volume_kg`
Optional: `gender`, `date_of_birth`, `phone_number`, `nin`, `community`, `num_plots`, `farm_size_ha`

Download a template with the exact headers from the Master Data page in the
app, or see `examples/` in this repo for a blank template and a filled-in
sample file.

## Security notes — read before sharing the link widely

- Farmer phone numbers and National ID numbers (NIN) are personal data. Treat
  the deployed URL and each LBA's login credentials accordingly.
- Each LBA's data is isolated by account (`lba_id`) at the database level —
  tested directly: logging in as one LBA cannot view, list, or export another
  LBA's farmers or lots, even by guessing a direct URL.
- Passwords are hashed with bcrypt, never stored in plain text. Sessions are
  signed cookies (`SECRET_KEY`), not stored server-side.
- **What's not built yet, by design, for a first version:** no "forgot
  password" self-service flow (you'd need to reset it directly in the
  database), no email verification on signup, no login rate-limiting. Fine
  for a small number of trusted LBAs; worth revisiting before a large public
  rollout.
- The "Clear all data" button only ever affects the logged-in LBA's own data,
  but there is still no undo and no backup — it's a real delete.
