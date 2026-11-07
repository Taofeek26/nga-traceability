# Components

Every component below is in [`css/lba-ui.css`](../css/lba-ui.css) (section number in
brackets). Prefer the macro from [`templates/macros.html`](../templates/macros.html)
when one exists. See them rendered at `preview/out/components.html` after running `build_preview.py`.

---

## Page header [3]

```jinja
{% call ui.page_header("Lot History", "12 lot(s) recorded.", eyebrow="Traceability") %}
  <a class="btn btn--accent" href="/lots/new">{{ ui.icon("plus") }}New lot</a>
{% endcall %}
```
Without actions: `{{ ui.page_header("Settings", "Configuration for this account.") }}`.
Section headings inside a page: `<div class="section-title"><h2>…</h2></div>`.

## Stat tiles [6]

```jinja
<section class="stats">
  {{ ui.stat("Delivered so far", ui.kg(delivered), "kg", icon_name="scale", meta="52% of potential") }}
  {{ ui.stat("Lots recorded", n_lots, icon_name="package", highlight=True) }}
</section>
```
`tone`: `""` gold · `"brown"` · `"green"` · `"red"`. Max one `highlight=True` per row.

## Summary strip [17]

```html
<div class="summary">
  <div class="summary__item"><div class="summary__label">Receipts</div><div class="summary__value">1301–1330</div></div>
  …
</div>
```

## Card [5]

```html
<div class="card">
  <div class="card__header">
    <div><div class="card__title">{{ ui.icon("truck") }}Delivery history</div><div class="card__subtitle">Optional</div></div>
    <a class="link-arrow" href="…">View all {{ ui.icon("arrow-right") }}</a>
  </div>
  <div class="card__body">…</div>          <!-- card__body--flush for tables -->
  <div class="card__footer">…buttons…</div> <!-- right-aligned; card__footer--between -->
</div>
```
A `<form class="card">` is fine — put the submit button in `card__footer`.

## Buttons [7]

```html
<a class="btn btn--accent" href="…">{{ ui.icon("plus") }}New lot</a>
<button class="btn btn--primary" type="submit">Save</button>
<a class="btn btn--secondary">…</a>  <a class="btn btn--soft">…</a>  <a class="btn btn--ghost">…</a>
<button class="btn btn--danger">…</button>  <button class="btn btn--danger-soft">…</button>
```
Sizes: `btn--sm` (32 px) · default (40 px) · `btn--lg` (48 px). `btn--block` full width,
`btn--icon` square icon-only (needs `aria-label`). Text link with arrow: `.link-arrow`.

## Form fields [8]

```html
<div class="form-grid">               <!-- form-grid--3 for 3 columns; .field--full spans all -->
  <div class="field">
    <label class="label" for="x">Label <span class="label__optional">(optional)</span></label>
    <input class="input" id="x" name="x">
    <span class="hint">Helper text.</span>
  </div>
</div>
```
- Select: `<select class="select">`. Textarea: `.textarea`. Invalid: add `.is-invalid` + `.field-error`.
- Unit add-on: `<div class="input-group"><span class="input-group__addon">₦</span><input class="input"></div>`
  (addon may go before or after the input).
- Leading icon: `<div class="input-group input-group--icon"><span class="input-group__icon">{{ ui.icon("search") }}</span><input class="input"></div>`.
- Range: `<div class="range-pair"><input class="input"><span class="range-pair__sep">–</span><input class="input"></div>`.
- Sectioned form: `.form-section` (left: `form-section__title` + `form-section__desc`, right: fields).
- Actions row outside a card footer: `.form-actions` (`.form-actions--end`).

## File dropzone [8]

```html
<label class="dropzone">
  <input type="file" name="file" accept=".xlsx" required
         onchange="this.parentElement.querySelector('.dropzone__file').textContent=this.files[0]?this.files[0].name:''">
  <span class="dropzone__icon">{{ ui.icon("upload", "lg") }}</span>
  <span class="dropzone__title">Drop your .xlsx here or <u>browse</u></span>
  <span class="dropzone__hint">…</span>
  <span class="dropzone__file"></span>
</label>
```

## Toolbar, search, chips [8]

```html
<form class="toolbar" method="get">
  <div class="input-group input-group--icon toolbar__search">…search input…</div>
  <div class="chips"><a class="chip is-active">All <span class="chip__count">412</span></a><a class="chip">Near limit</a></div>
  <div class="toolbar__end">…</div>
</form>
```
Put the toolbar as the first child of a `.card`, directly above the `.table-wrap`.

## Table [9]

```html
<div class="table-wrap">
  <table class="table">                     <!-- table--compact for dense lists -->
    <thead><tr><th>Farmer</th><th class="is-num">Volume (kg)</th><th class="hide-sm">Note</th><th class="is-action"></th></tr></thead>
    <tbody><tr>
      <td><a class="cell-person" href="…">{{ ui.avatar(f.first_name, f.surname) }}
          <span><span class="cell-primary">Name</span><span class="cell-secondary mono">FC-0012</span></span></a></td>
      <td class="is-num">{{ ui.kg(v, 2) }}</td>
      <td class="hide-sm is-muted">…</td>
      <td class="is-action"><a class="link-arrow" href="…">View {{ ui.icon("chevron-right") }}</a></td>
    </tr></tbody>
    <tfoot><tr><td>Total</td><td class="is-num">…</td></tr></tfoot>
  </table>
</div>
```
- Always wrap in `.table-wrap`; always use `<thead>`/`<tbody>`.
- Numbers: `.is-num` (right-aligned, tabular). Row action column: `.is-action`.
- Codes / receipt numbers: `<span class="code-tag">1301</span>`.
- `.hide-sm` hides a column under 640 px — keep the identifying column and status visible.

## Description list [9]

```html
<dl class="dl"><dt>Phone number</dt><dd>0803…</dd>…</dl>
```

## Avatar [10]

`{{ ui.avatar(first, last) }}` · sizes `"lg"`, `"xl"` · tone `"gold"`.

## Badges [11]

`{{ ui.farmer_status(f.active, pct) }}` for quota status. Manual:
`<span class="badge badge--ok|warn|full|inactive|gold|brown">Text</span>`;
add `badge--plain` to drop the dot (e.g. category tags).

## Alerts [12]

`{{ ui.alert(msg, "success") }}` · `"error"` · `"warning"` · `"info"`, optional `title=`.
Place directly under the page header.

## Progress [13]

```jinja
{{ ui.progress(pct) }}            {# size: "sm" | "lg" #}
{{ ui.mini_meter(pct) }}          {# bar + % for table cells #}
<div class="meter"><div class="meter__head"><span class="meter__label">Quota used</span><span class="meter__value">97%</span></div>{{ ui.progress(pct, "lg") }}</div>
```

## Empty state [14]

`{{ ui.empty_state("No lots yet", "Explain the next step.", "package", "/lots/new", "Record first lot") }}`
— last two args optional. Use inside `card__body--flush` or directly in a `.card`.

## Steps [15]

```html
<ol class="steps"><li class="step is-done"><span class="step__num"></span><span class="step__title">…</span><span class="step__text">…</span></li>…</ol>
```

## Danger zone [16]

See `templates/pages/upload.html`. Always: icon, red title, consequence text,
type-to-confirm input, `btn--danger`, and a JS `confirm()`.

## Action bar [18]

Sticky dark bar at the bottom of long result pages (lot result). Contains a short
summary and at most two buttons.

## Icons

`{{ ui.icon("name") }}` · sizes `"sm"` (16) / default (18) / `"lg"` (22) · pass a third
argument as `aria-label` when the icon is the only content.

Available: dashboard, users, user, plus, plus-circle, history, database, settings,
logout, search, menu, x, chevron-right, arrow-left, arrow-right, download, upload,
file-sheet, package, scale, truck, receipt, wallet, gift, map-pin, leaf, calendar,
phone, id-card, check, check-circle, alert-circle, alert-triangle, info, trash,
power, percent, sparkles, lock, shield.

## Formatting helpers

`{{ ui.kg(value) }}` → `12,346` · `{{ ui.kg(value, 2) }}` → `12,345.60` ·
`{{ ui.naira(value) }}` → `₦43,500`.
