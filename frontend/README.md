# LBA Traceability — Frontend

React + TypeScript + Vite single-page app. Ported from the original
Jinja2 templates — same CSS (`public/styles/`), same icon sprite
(`src/components/IconSprite.tsx`), same component behavior
(`src/components/ui.tsx`), calling the AWS backend in `../backend/`
instead of server-rendering.

## Build

```
npm install
npm run build
```

`VITE_API_BASE_URL` must point at the deployed HTTP API's base URL (the
`ApiUrl` output of the backend stack). It's set as a Production
environment variable on the Vercel project (not committed — see the root
`.gitignore`'s `.env*` rule); for local dev, put it in `.env.local`.

## Deployment

Live at https://jimgaf-traceability.vercel.app. The Vercel project is
connected to this GitHub repo with **Root Directory set to `frontend`**
(required — without it, a git-triggered build runs from the repo root,
finds the old Python app's `requirements.txt` instead of this
directory's `package.json`, and fails). Pushing to `main` auto-deploys;
no manual `vercel --prod` needed.

The original production app (Vercel project `nigeria-lba-traceability`,
on the FastAPI+Jinja2+Neon stack) is left running untouched as a
rollback fallback.

## Status

All pages built: auth, dashboard, farmers, farmer detail, lots, new lot
(with preferred-farmer search), lot result (certification + receipts),
settings, team, master data upload, documents, and audit log.
