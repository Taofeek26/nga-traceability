# LBA Traceability — Frontend

React + TypeScript + Vite single-page app. Ported from `templates/` — same
CSS (`public/styles/`), same icon sprite (`src/components/IconSprite.tsx`),
same component behavior (`src/components/ui.tsx`), calling the AWS backend
in `../backend/` instead of server-rendering.

## Build

```
npm install
npm run build
```

`VITE_API_BASE_URL` (see `.env.production`) must point at the deployed
HTTP API's base URL (the `ApiUrl` output of the backend stack).

## Status

Built so far: auth (login/signup), dashboard — the full vertical slice
proving frontend ↔ API Gateway ↔ Lambda ↔ Aurora end to end. The
remaining pages (farmers, farmer detail, lots, new lot, lot result,
settings, users, upload) are not yet built — see
`html/frontend-backend-split-plan.html` for the page-by-page plan.
