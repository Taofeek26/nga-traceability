# Foundations

All values live in [`css/tokens.css`](../css/tokens.css). Components reference
**semantic** tokens (`--color-*`, `--space-*`), which map onto the brand palette.

## Colour

### Brand palette (locked — unchanged from the original app)

| Token | Hex | Role |
|---|---|---|
| `--brown-dark` | `#2A1B12` | Sidebar, body text, dark highlight tile, action bar |
| `--brown` | `#4B2F21` | Headings, primary buttons, step numbers |
| `--brown-mid` | `#6B4A34` | Links, secondary text |
| `--taupe` | `#8A7A6E` | Muted text, labels, table headers |
| `--cream` | `#F7F2EC` | Page background, sunken surfaces, table header |
| `--sand` | `#EFE8DF` | Hairlines, soft buttons, neutral badges, avatars |
| `--gold` | `#C89B3C` | Accent: active nav, main CTA, focus ring, progress |
| `--red` | `#E1251B` | Errors, at-limit, destructive |
| `--green` | `#2E7D32` | Success, OK status |
| `--white` | `#FFFFFF` | Cards, inputs |

### Derived tints

Already in the original app: `--green-tint`, `--amber` / `--amber-tint` (near-limit),
`--red-tint`, `--red-border`, `--red-wash`.

Added (mixed from brand colours only): `--gold-tint` (soft accent backgrounds),
`--gold-hover` (gold text on light backgrounds — plain gold fails contrast on white),
`--sand-line` (input borders), `--taupe-light` (placeholders), `--brown-ink-2` (sidebar hover).

### Usage rules

- One gold CTA per view. Gold is a highlight, not a fill colour for large areas.
- Gold **text** on white/cream must use `--gold-hover`, not `--gold`.
- Status colour is always paired with a label (badge text) — never colour alone.
- Large dark surfaces are limited to the sidebar, the auth side panel, one
  highlighted stat tile and the sticky action bar.

## Typography

Font: **Inter** (fallback: system UI stack). Numbers use `tabular-nums`.

| Token | Size | Use |
|---|---|---|
| `--text-xs` | 12 | Table headers (uppercase), badges, hints |
| `--text-sm` | 13 | Labels, meta, secondary |
| `--text-base` | 14 | Body, inputs, tables |
| `--text-md` | 15 | Card titles, descriptions |
| `--text-xl` | 20 | Section titles, summary values |
| `--text-2xl` | 26 | Page titles |
| `--text-3xl` | 30 | Stat values |

Weights: 400 body · 500 nav/medium · 600 labels/titles · 700 page titles/values.
Uppercase is used only for eyebrows, table headers and summary labels, with `--tracking-caps`.

## Spacing

4 px grid: `--space-1` (4) → `--space-16` (64).
Page gutter 32 px (16 px on mobile). Card padding 20 px. Gap between cards 24 px.
Gap between stat tiles 16 px. Field gap 20 px.

## Radius

`--radius-sm` 6 (small buttons, code tags) · `--radius-md` 8 (buttons, inputs, nav)
· `--radius-lg` 12 (cards, stats, panels) · `--radius-full` (badges, avatars, chips).

## Elevation

Shadows are brown-tinted, never grey. Cards use `--shadow-xs` plus a 1 px sand
border; hover/interactive uses `--shadow-md`; floating elements (drawer, action bar)
use `--shadow-lg`. Focus is always `--ring-focus` (gold, 3 px).

## Layout

- Sidebar 248 px fixed; collapses to a slide-out drawer below 900 px.
- Content max width 1200 px; form pages use `content--narrow` (760 px).
- Breakpoints: 1100 px (two-column grids stack), 900 px (drawer), 640 px (forms stack, 2-up stats).
