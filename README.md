# SolaraX

Solar analytics platform (Vue frontend first; FastAPI and ML services later).

## Prerequisites

- Node.js `^22.18.0 || >=24.12.0`
- npm

## Frontend (`apps/web`)

```powershell
cd apps/web
npm install
npm run dev
```

Other scripts:

- `npm run build` — production build
- `npm run test:unit` — Vitest
- `npm run lint` — ESLint
- `npm run format` — Prettier

Copy `apps/web/.env.example` to `apps/web/.env.local` and adjust `VITE_*` values as needed.

## Docs

- Design: `docs/superpowers/specs/2026-08-15-vue-frontend-setup-design.md`
