# SolaraX Vue Frontend Setup Design

**Date:** 2026-08-15  
**Status:** Approved (conversation) — pending user review of this written spec  
**Scope:** Frontend-only scaffold (round 1)

## Goal

Scaffold a production-ready Vue 3 + Vite + TypeScript SPA under `apps/web`, using the official [Vue Quick Start](https://vuejs.org/guide/quick-start.html) path (`npm create vue@latest`), with a monorepo layout that can later host FastAPI and other SolaraX stack pieces.

## Decisions Locked

| Topic | Choice |
|--------|--------|
| Scope this round | Frontend only (Approach A) |
| Scaffold tool | Official `create-vue` |
| Language | TypeScript |
| Router | Vue Router — Yes |
| State | Pinia — Yes |
| Repo layout | `apps/web` |
| Tooling | ESLint + Prettier + Vitest + Vue DevTools |
| E2E | No (defer) |
| JSX | No |
| Package manager | npm |
| Charts / maps deps | Defer ECharts + Leaflet until after base scaffold |

## Approach

**Chosen: Approach A — Official `create-vue` into `apps/web`**

- Matches current Vue docs (Node `^22.18.0 || >=24.12.0`; this machine has Node v25.9.0).
- Composition API + `<script setup>` by default.
- Avoids manual Router/Pinia/ESLint wiring (Approach B) and Nuxt SSR weight (Approach C).

## Repository Layout

```text
SolaraX/
├── apps/
│   └── web/                 # Vue 3 + Vite + TypeScript
│       ├── src/
│       │   ├── assets/
│       │   ├── components/  # presentational UI
│       │   ├── composables/ # reusable Composition API logic
│       │   ├── layouts/     # app shell / nav
│       │   ├── router/
│       │   ├── stores/      # Pinia
│       │   ├── services/    # HTTP / API clients (FastAPI later)
│       │   ├── types/
│       │   ├── views/       # route pages
│       │   ├── App.vue
│       │   └── main.ts
│       ├── package.json
│       └── ...
├── docs/
│   └── superpowers/
│       └── specs/
├── README.md
└── LICENSE
```

**Later (out of scope):** `apps/api` (FastAPI), optional `packages/` for shared types/clients, CI, Vercel, CV/ML apps.

## Coding Practices

- Composition API + `<script setup lang="ts">` only for new code; no Options API; no JSX.
- `views/` = route pages; `components/` = reusable UI; `composables/` = `useX` logic; `stores/` = cross-page state; `services/` = HTTP only; `types/` = shared TS types.
- Path alias `@/` → `src/`.
- Env via `.env` / `.env.local` with `VITE_*` prefixes only.
- ESLint + Prettier enforced; Vitest for composables/stores unit tests.
- Post-scaffold: ensure `composables/`, `services/`, `types/`, `layouts/` exist (create empty dirs + `.gitkeep` if create-vue omits them).

## Scaffold Commands

From repo root `C:\Users\User\SolaraX` (PowerShell):

```powershell
mkdir apps
cd apps
npm create vue@latest web
```

**create-vue prompts:**

| Prompt | Answer |
|--------|--------|
| TypeScript | Yes |
| JSX | No |
| Vue Router | Yes |
| Pinia | Yes |
| Vitest | Yes |
| End-to-End Testing | No |
| ESLint | Yes |
| Prettier | Yes |
| Vue DevTools 7 | Yes |

```powershell
cd web
npm install
npm run dev
```

**Scripts:** `npm run build`, `npm run test:unit`, `npm run lint`, `npm run format`.

## Error Handling (frontend baseline)

- Centralize API errors in `services/` (throw typed errors; surfaces handle UI messaging).
- Router: catch-all / 404 view after routes exist.
- No backend retry policy in this round (no API yet).

## Testing

- Vitest unit tests for composables and Pinia stores as they are added.
- No E2E in this round.
- Smoke check: `npm run dev` loads; `npm run build` succeeds; `npm run lint` clean after scaffold tweaks.

## Out of Scope

FastAPI, Supabase, DuckDB, YOLO/ONNX, ECharts, Leaflet, GitHub Actions, Vercel, Hugging Face Spaces.

## Success Criteria

1. `apps/web` exists and runs with `npm run dev`.
2. TypeScript, Router, Pinia, ESLint, Prettier, Vitest enabled.
3. Folder conventions above in place for SolaraX growth.
4. Root README updated to point at `apps/web` setup commands.
