# CLAUDE.md — LBA Traceability Design System

You are working with the design system for the **Nigeria LBA Level Traceability** app
(FastAPI + Jinja2, server-rendered, no JS framework). This file is the contract.
Read it fully before touching any template or stylesheet.

## Golden rules

1. **The colour palette is locked.** The ten brand colours in `css/tokens.css`
   (`--brown-dark #2A1B12`, `--brown #4B2F21`, `--brown-mid #6B4A34`, `--taupe #8A7A6E`,
   `--cream #F7F2EC`, `--sand #EFE8DF`, `--gold #C89B3C`, `--red #E1251B`,
   `--green #2E7D32`, `--white #FFFFFF`) are the app's original theme. Never change,
   add to, or "improve" them. New tints are allowed only if mixed from these and
   added to the *Derived* block in `tokens.css` with a comment.
2. **No raw hex or px values in templates.** Use component classes from
   `css/lba-ui.css`. If an inline `style=""` is unavoidable, use tokens
   (`var(--space-4)`), never literals.
3. **Use the macros.** Import `{% import "macros.html" as ui %}` in every page and
   use `ui.page_header`, `ui.stat`, `ui.alert`, `ui.farmer_status`, `ui.progress`,
   `ui.empty_state`, `ui.icon`, `ui.kg`, `ui.naira` instead of hand-writing that markup.
4. **Never change backend contracts.** Form `action`s, `method`s, input `name`s,
   URLs and the template context variables listed in `docs/pages.md` must stay
   exactly as they are. The redesign is presentation-only.
5. **One stylesheet pair only.** Pages load `tokens.css` then `lba-ui.css`.
   Don't add per-page `<style>` blocks; extend `lba-ui.css` instead, in the
   matching numbered section, following its naming (`block__part--modifier`, `is-state`).
6. **Status thresholds live in one place**: `ui.farmer_status` / `ui.progress`
   (≥ 90 % → warn, ≥ 100 % → danger). Don't re-implement them in a page.
7. **Every page must work at 375 px wide.** Hide secondary table columns with
   `.hide-sm`; never let the page scroll horizontally (tables scroll inside `.table-wrap`).

## Repository map

```
design-system/
├── CLAUDE.md               ← you are here (rules)
├── README.md               ← human overview + install steps
├── css/
│   ├── tokens.css          ← colours, type, spacing, radius, shadows (source of truth)
│   └── lba-ui.css          ← every component, numbered sections 1–20
├── templates/              ← drop-in Jinja templates for the real app
│   ├── base.html           ← app shell: sidebar, topbar, breadcrumbs
│   ├── auth_base.html      ← split-screen shell for login/signup
│   ├── macros.html         ← component macros
│   ├── partials/icons.html ← inline SVG sprite (ui.icon("name"))
│   └── pages/*.html        ← one reference template per app page
├── docs/
│   ├── foundations.md      ← tokens explained, when to use which colour
│   ├── components.md       ← every component with copy-paste markup
│   └── pages.md            ← per-page layout blueprint + context variables
└── preview/
    ├── build_preview.py    ← renders all pages with mock data → preview/out/
    ├── components.html     ← component gallery source (rendered into out/)
    └── out/                ← generated previews (do not edit)
```

## Applying the design system to the app (migration)

When asked to "apply / install the design system", do exactly this:

1. Copy CSS: `design-system/css/tokens.css` and `lba-ui.css` → `static/ds/`.
2. Copy `design-system/templates/base.html`, `auth_base.html`, `macros.html`,
   and `partials/` → `templates/` (overwrite `base.html`).
3. Copy every file in `design-system/templates/pages/` → `templates/`
   (same filenames as the existing templates; overwrite).
4. Keep `static/style.css` until every page is migrated, then delete it and
   remove any link to it.
5. Verify: run `venv/bin/python design-system/preview/build_preview.py`
   (must finish without errors), then run the app and click through every
   nav item, a farmer detail, a lot result, login and signup. Check 375 px width.

## Building something new

- **New page** → extend `base.html`, set `{% block title %}`, add `{% block crumbs %}`
  if it's nested, start with `ui.page_header`, then compose from: `.stats` row →
  `.card` (with `card__header` / `card__body` / `card__footer`) → `.table` inside
  `.table-wrap`. Form pages set `{% set narrow = true %}` and use `.form-section`.
  Add the page to `PAGES` in `preview/build_preview.py` with mock data.
- **New nav item** → add `ui.nav_link(...)` in `base.html` under the right
  `nav__section`, pick an icon from the sprite.
- **New icon** → add a `<symbol id="i-name" viewBox="0 0 24 24">` to
  `partials/icons.html`: outline only, 24 px grid, no fills, matches Lucide style.
- **New component** → add a numbered section to `lba-ui.css`, document it in
  `docs/components.md`, add an example to `preview/components.html`.

## Choosing components (quick reference)

| Need | Use |
|---|---|
| Page title + primary action | `ui.page_header(...)` with `{% call %}` for buttons |
| Key numbers | `.stats` + `ui.stat(...)` (one `highlight=True` max per row) |
| Inline key figures in a header | `.summary` |
| List of records | `.card` › `.table-wrap` › `.table` |
| Person in a table | `.cell-person` + `ui.avatar` + `.cell-primary/.cell-secondary` |
| Codes, receipt numbers | `.code-tag` or `.mono` |
| Feedback after a POST | `ui.alert(msg, "success")` / `ui.alert(error, "error")` |
| Nothing to show | `ui.empty_state(...)` with a CTA when there's an obvious next step |
| Destructive action | `.danger-zone` + `.btn--danger` + type-to-confirm |
| Primary CTA | `.btn--accent` (gold) for the one main action per page; `.btn--primary` (brown) for form submits |

## Button hierarchy

- `btn--accent` (gold): the single most important action on a page (New lot, Export).
- `btn--primary` (brown): submitting a form.
- `btn--secondary` (white outlined): alternative actions.
- `btn--soft` / `btn--ghost`: tertiary, toolbar, table-row actions.
- `btn--danger`: irreversible only, always inside a `.danger-zone`.
