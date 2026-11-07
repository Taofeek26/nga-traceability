"""Render every reference page in design-system/templates/pages with mock data
into static HTML files under design-system/preview/out/, so the design can be
reviewed in a browser without Postgres or a login.

    venv/bin/python design-system/preview/build_preview.py
    python3 -m http.server 8766 --directory design-system/preview/out

It also acts as a smoke test: any Jinja error in a reference template fails here.
"""
import shutil
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, StrictUndefined

DS = Path(__file__).resolve().parent.parent
OUT = DS / "preview" / "out"

env = Environment(
    loader=FileSystemLoader([str(DS / "templates"), str(DS / "templates" / "pages"), str(DS / "preview")]),
    undefined=StrictUndefined,
    autoescape=True,
)


def req(path):
    return SimpleNamespace(url=SimpleNamespace(path=path))


def farmer(code, first, last, community, potential, delivered, active=True, **extra):
    return dict(farmer_code=code, first_name=first, surname=last, community=community,
                potential_volume_kg=potential, delivered=delivered, active=active, **extra)


FARMERS = [
    farmer("FC-0012", "Adaeze", "Okafor", "Agbor", 1800, 1740),
    farmer("FC-0031", "Babatunde", "Adeyemi", "Owa-Oyibu", 2200, 2200),
    farmer("FC-0047", "Chinedu", "Eze", "Ika", 1500, 610),
    farmer("FC-0058", "Fatima", "Bello", None, 900, 120),
    farmer("FC-0063", "Ngozi", "Nwosu", "Agbor", 2600, 2390),
    farmer("FC-0079", "Oluwaseun", "Balogun", "Umunede", 1300, 0, active=False),
]
LOTS = [
    dict(id=14, lot_date="2026-10-28", receipt_start=1301, receipt_end=1330, total_volume_kg=4120.5, n_farmers=30, note="Broker: Emeka · truck LAG-552"),
    dict(id=13, lot_date="2026-10-19", receipt_start=1271, receipt_end=1300, total_volume_kg=3875.0, n_farmers=30, note=None),
    dict(id=12, lot_date="2026-10-07", receipt_start=1251, receipt_end=1270, total_volume_kg=2410.25, n_farmers=20, note="Wet season top-up"),
]
COMMON = dict(lba_name="Agbor Buying Station", msg="", error="")

PAGES = {
    "dashboard": ("/", dict(n_farmers=412, n_active=398, potential=612500, delivered=318240.4, n_lots=3,
                            recent_lots=LOTS, near_limit=[f for f in FARMERS if f["active"] and f["delivered"] >= 0.9 * f["potential_volume_kg"]])),
    "farmers": ("/farmers", dict(farmers=FARMERS, q="")),
    "farmer_detail": ("/farmers/FC-0012", dict(
        f=dict(FARMERS[0], gender="Female", date_of_birth="1984-03-12", phone_number="0803 555 0192",
               nin="12345678901", num_plots=3, farm_size_ha=2.4),
        delivered=1740, remaining=60, premium_rate=25, premium_accrued=43500, other_incentives=15000,
        total_entitlement=58500, msg="Incentive recorded.",
        incentives=[dict(incentive_date="2026-09-02", type="Training stipend", amount=10000, note="GAP training"),
                    dict(incentive_date="2026-10-11", type="Bonus", amount=5000, note=None)],
        deliveries=[dict(lot_date="2026-10-28", receipt_number=1304, allocated_volume_kg=142.37, lot_id=14),
                    dict(lot_date="2026-10-19", receipt_number=1288, allocated_volume_kg=98.1, lot_id=13)])),
    "lots": ("/lots", dict(lots=LOTS)),
    "new_lot": ("/lots/new", dict(today="2026-11-02", n_eligible=287)),
    "lot_result": ("/lots/14", dict(lot=LOTS[0], rows=[
        dict(receipt_number=1301 + i, farmer_code=f["farmer_code"], first_name=f["first_name"], surname=f["surname"],
             community=f["community"], allocated_volume_kg=v)
        for i, (f, v) in enumerate(zip(FARMERS, [182.4, 96.75, 141.0, 77.3, 210.05, 120.0]))])),
    "upload": ("/upload", dict(msg="Imported 412 farmers (9 new, 403 updated).")),
    "settings": ("/settings", dict(rate=25)),
    "login": ("/login", dict(error="", msg="")),
    "signup": ("/signup", dict(error="")),
}

# Also render the empty / error variants that matter visually
VARIANTS = {
    "dashboard_empty": ("dashboard", "/", dict(n_farmers=0, n_active=0, potential=0, delivered=0, n_lots=0, recent_lots=[], near_limit=[])),
    "farmers_empty": ("farmers", "/farmers", dict(farmers=[], q="")),
    "new_lot_blocked": ("new_lot", "/lots/new", dict(today="2026-11-02", n_eligible=0, error="Receipt range is larger than the number of eligible farmers.")),
    "login_error": ("login", "/login", dict(error="Incorrect email or password.", msg="")),
}


def render(page, path, ctx):
    html = env.get_template(f"{page}.html").render(request=req(path), **{**COMMON, **ctx})
    # Point asset + nav links at the local preview files
    html = html.replace("/static/ds/", "css/")
    for name, (p, _) in PAGES.items():
        html = html.replace(f'href="{p}"', f'href="{name}.html"')
    return html


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "css").mkdir(exist_ok=True)
    for css in (DS / "css").glob("*.css"):
        shutil.copy(css, OUT / "css" / css.name)

    links = []
    for name, (path, ctx) in PAGES.items():
        (OUT / f"{name}.html").write_text(render(name, path, ctx))
        links.append(name)
    for name, (page, path, ctx) in VARIANTS.items():
        (OUT / f"{name}.html").write_text(render(page, path, ctx))
        links.append(name)

    gallery = env.get_template("components.html").render().replace("/static/ds/", "css/")
    (OUT / "components.html").write_text(gallery)

    items = "".join(f'<li><a href="{n}.html">{n.replace("_", " ").title()}</a></li>' for n in links)
    (OUT / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>LBA UI preview</title><link rel="stylesheet" href="css/tokens.css"><link rel="stylesheet" href="css/lba-ui.css">'
        '<main class="content content--narrow"><header class="page-header"><div><div class="page-header__eyebrow">Design system</div>'
        '<h1 class="page-header__title">Page previews</h1><p class="page-header__desc">Reference templates rendered with mock data. '
        'Open <a href="components.html">components.html</a> for the component gallery.</p></div></header>'
        f'<div class="card"><div class="card__body"><ul style="columns:2;margin:0;">{items}</ul></div></div></main>'
    )
    print(f"Rendered {len(links)} pages to {OUT}")


if __name__ == "__main__":
    main()
