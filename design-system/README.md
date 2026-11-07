# LBA Traceability — Design System

A modern layout and component library for the Nigeria LBA Level Traceability app.
It **keeps the original colour theme exactly** (dark brown, cream, sand, gold) and
replaces the page structure and components with a cleaner, more modern system:

- Icon sidebar with grouped sections, account card and mobile slide-out drawer
- Sticky translucent top bar with breadcrumbs
- Page headers with eyebrow, description and action buttons
- KPI stat tiles with icon chips, summary strips, cards with header/body/footer
- Data tables with avatars, code tags, inline quota meters and status badges
- Sectioned forms with unit add-ons (kg, ₦), receipt range input, file dropzone
- Alerts with icons, empty states, onboarding steps, danger zone
- Split-screen login and signup

Built for the existing stack: plain CSS + Jinja2 macros, no build step, no JS framework.

## Quick start

Preview every page with mock data (no database needed):

```bash
venv/bin/python design-system/preview/build_preview.py
```

```bash
python3 -m http.server 8766 --directory design-system/preview/out
```

Then open http://localhost:8766 (page previews) and
http://localhost:8766/components.html (component gallery).

## Installing into the app

Ask Claude Code: *"Apply the design system in `design-system/` to the app — follow
`design-system/CLAUDE.md`."* Or by hand:

```bash
mkdir -p static/ds templates/partials
cp design-system/css/*.css static/ds/
cp design-system/templates/base.html design-system/templates/auth_base.html design-system/templates/macros.html templates/
cp design-system/templates/partials/icons.html templates/partials/
cp design-system/templates/pages/*.html templates/
```

No Python changes are needed: the page templates use exactly the same context
variables, form fields and URLs as the current ones.

## Documentation

| File | What it covers |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Rules for Claude Code (and humans) working on the UI |
| [docs/foundations.md](docs/foundations.md) | Colour roles, typography, spacing, radius, elevation |
| [docs/components.md](docs/components.md) | Every component with copy-paste markup |
| [docs/pages.md](docs/pages.md) | Layout blueprint and context variables for each page |

## Notes

- The Inter font loads from Google Fonts; if it's unavailable the system font is used.
  Remove the three font `<link>` tags in `base.html` / `auth_base.html` to go fully offline.
- `preview/out/` is generated; don't edit it by hand.
