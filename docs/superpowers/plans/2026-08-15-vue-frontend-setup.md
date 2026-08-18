# Vue Frontend Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold SolaraX’s Vue 3 + Vite + TypeScript SPA under `apps/web` with Router, Pinia, ESLint, Prettier, Vitest, and SolaraX folder conventions ready for FastAPI later.

**Architecture:** Official `create-vue` scaffolds `apps/web`. We then add SolaraX directories (`composables/`, `services/`, `types/`, `layouts/`), a typed API error helper, a catch-all 404 route, env template, and root README pointers. No charts/maps/backend in this plan.

**Tech Stack:** Vue 3, Vite, TypeScript, Vue Router, Pinia, Vitest, ESLint, Prettier, npm (create-vue@3.x)

**Spec:** `docs/superpowers/specs/2026-08-15-vue-frontend-setup-design.md`

## Global Constraints

- Node.js version floor: `^22.18.0 || >=24.12.0` (machine has v25.9.0)
- Package manager: `npm` only
- App path: `apps/web` (do not scaffold at repo root)
- Language: TypeScript; Composition API + `<script setup lang="ts">` only; no JSX; no Options API for new code
- Tooling: ESLint + Prettier + Vitest; no E2E
- Env vars: `VITE_*` prefix only
- Path alias: `@/` → `src/`
- Out of scope: FastAPI, Supabase, DuckDB, YOLO/ONNX, ECharts, Leaflet, CI, Vercel, Hugging Face
- OS shell: PowerShell on Windows (`C:\Users\User\SolaraX`)
- Prefer non-interactive `create-vue` feature flags (no prompts)
- create-vue 3.23.x has no `--vue-devtools` flag; skip DevTools plugin unless already generated — do not block on it

---

## File Structure (target)

| Path | Responsibility |
|------|----------------|
| `apps/web/` | Vue SPA package (create-vue output + SolaraX layout) |
| `apps/web/src/views/` | Route pages only |
| `apps/web/src/components/` | Presentational UI |
| `apps/web/src/composables/` | Reusable `useX` Composition API logic |
| `apps/web/src/layouts/` | App shell / nav wrappers |
| `apps/web/src/stores/` | Pinia stores |
| `apps/web/src/services/` | HTTP/API clients + typed errors |
| `apps/web/src/types/` | Shared TypeScript types |
| `apps/web/src/router/` | Vue Router config |
| `apps/web/.env.example` | Documented `VITE_*` keys |
| `apps/web/src/views/NotFoundView.vue` | Catch-all 404 page |
| `README.md` | Root pointers to `apps/web` setup |

---

### Task 1: Scaffold `apps/web` with create-vue

**Files:**
- Create: `apps/web/**` (via create-vue)
- Modify: none yet

**Interfaces:**
- Consumes: none
- Produces: runnable Vue package at `apps/web` with TS, Router, Pinia, Vitest, ESLint, Prettier

- [ ] **Step 1: Verify Node version**

Run from `C:\Users\User\SolaraX`:

```powershell
node -v
npm -v
```

Expected: Node matches `^22.18.0 || >=24.12.0` (e.g. `v25.x`); npm prints a version.

- [ ] **Step 2: Create `apps` and scaffold non-interactively**

```powershell
cd C:\Users\User\SolaraX
New-Item -ItemType Directory -Path apps -Force | Out-Null
cd apps
npm create vue@latest web -- --typescript --router --pinia --vitest --eslint --prettier
```

Expected: `apps/web` created with `package.json`, `src/`, `vite.config.ts` (or `.mts`), router, and pinia.

If the directory already exists from a failed attempt:

```powershell
npm create vue@latest web -- --force --typescript --router --pinia --vitest --eslint --prettier
```

- [ ] **Step 3: Install dependencies**

```powershell
cd C:\Users\User\SolaraX\apps\web
npm install
```

Expected: `node_modules` present; exit code 0.

- [ ] **Step 4: Smoke — unit test script exists and runs**

```powershell
cd C:\Users\User\SolaraX\apps\web
npm run test:unit -- --run
```

Expected: Vitest runs and exits 0 (default create-vue sample tests pass).

- [ ] **Step 5: Smoke — production build**

```powershell
cd C:\Users\User\SolaraX\apps\web
npm run build
```

Expected: build succeeds; `apps/web/dist` created.

- [ ] **Step 6: Commit scaffold**

```powershell
cd C:\Users\User\SolaraX
git add apps/web
git commit -m "chore: scaffold Vue 3 app in apps/web with create-vue"
```

Expected: commit created. If Cursor re-adds `Co-authored-by`, strip it in an external terminal or with Attribution disabled before pushing.

---

### Task 2: Add SolaraX source folders

**Files:**
- Create: `apps/web/src/composables/.gitkeep`
- Create: `apps/web/src/services/.gitkeep`
- Create: `apps/web/src/types/.gitkeep`
- Create: `apps/web/src/layouts/.gitkeep`
- Modify: none (keep create-vue `components/`, `views/`, `stores/`, `router/` as-is)

**Interfaces:**
- Consumes: scaffold from Task 1
- Produces: empty convention directories for later features

- [ ] **Step 1: Create missing directories**

```powershell
cd C:\Users\User\SolaraX\apps\web\src
New-Item -ItemType Directory -Force -Path composables, services, types, layouts | Out-Null
New-Item -ItemType File -Force -Path composables\.gitkeep, services\.gitkeep, types\.gitkeep, layouts\.gitkeep | Out-Null
```

Expected: four folders exist under `src/`.

- [ ] **Step 2: Confirm path alias `@/`**

Open `apps/web/tsconfig.app.json` (or `tsconfig.json` / `vite.config.*`) and confirm `@/*` → `./src/*` (create-vue default). If missing, add to `tsconfig.app.json`:

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

And in `vite.config.ts`:

```ts
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
```

(Only edit if create-vue omitted the alias; do not duplicate plugins already present.)

- [ ] **Step 3: Commit**

```powershell
cd C:\Users\User\SolaraX
git add apps/web/src/composables apps/web/src/services apps/web/src/types apps/web/src/layouts
git commit -m "chore: add SolaraX src folder conventions under apps/web"
```

---

### Task 3: Typed API error helper (`services/`)

**Files:**
- Create: `apps/web/src/services/httpError.ts`
- Create: `apps/web/src/services/httpError.spec.ts`
- Delete: `apps/web/src/services/.gitkeep` (once real files exist)

**Interfaces:**
- Consumes: none
- Produces:
  - `class HttpError extends Error` with `readonly status: number`, `readonly body: unknown`
  - `function toHttpError(error: unknown): HttpError`

- [ ] **Step 1: Write the failing test**

Create `apps/web/src/services/httpError.spec.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { HttpError, toHttpError } from './httpError'

describe('HttpError', () => {
  it('stores status and body', () => {
    const err = new HttpError('Nope', 404, { detail: 'missing' })
    expect(err.message).toBe('Nope')
    expect(err.status).toBe(404)
    expect(err.body).toEqual({ detail: 'missing' })
    expect(err.name).toBe('HttpError')
  })
})

describe('toHttpError', () => {
  it('returns the same instance when already HttpError', () => {
    const original = new HttpError('x', 500, null)
    expect(toHttpError(original)).toBe(original)
  })

  it('wraps a normal Error', () => {
    const wrapped = toHttpError(new Error('boom'))
    expect(wrapped).toBeInstanceOf(HttpError)
    expect(wrapped.message).toBe('boom')
    expect(wrapped.status).toBe(0)
  })

  it('wraps unknown values', () => {
    const wrapped = toHttpError('weird')
    expect(wrapped).toBeInstanceOf(HttpError)
    expect(wrapped.message).toBe('weird')
    expect(wrapped.status).toBe(0)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
cd C:\Users\User\SolaraX\apps\web
npm run test:unit -- --run src/services/httpError.spec.ts
```

Expected: FAIL (module `./httpError` not found or exports missing).

- [ ] **Step 3: Write minimal implementation**

Create `apps/web/src/services/httpError.ts`:

```ts
export class HttpError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(message: string, status: number, body: unknown = null) {
    super(message)
    this.name = 'HttpError'
    this.status = status
    this.body = body
  }
}

export function toHttpError(error: unknown): HttpError {
  if (error instanceof HttpError) {
    return error
  }

  if (error instanceof Error) {
    return new HttpError(error.message, 0, null)
  }

  return new HttpError(String(error), 0, null)
}
```

Remove `apps/web/src/services/.gitkeep` if present.

- [ ] **Step 4: Run test to verify it passes**

```powershell
cd C:\Users\User\SolaraX\apps\web
npm run test:unit -- --run src/services/httpError.spec.ts
```

Expected: PASS (all four tests).

- [ ] **Step 5: Commit**

```powershell
cd C:\Users\User\SolaraX
git add apps/web/src/services
git commit -m "feat: add typed HttpError helper for API services"
```

---

### Task 4: Catch-all 404 view and route

**Files:**
- Create: `apps/web/src/views/NotFoundView.vue`
- Modify: `apps/web/src/router/index.ts` (add final catch-all route)
- Test: manual route check + `npm run build`

**Interfaces:**
- Consumes: Vue Router from Task 1
- Produces: route `{ path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView }`

- [ ] **Step 1: Add `NotFoundView.vue`**

Create `apps/web/src/views/NotFoundView.vue`:

```vue
<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <main>
    <h1>Page not found</h1>
    <p>The page you requested does not exist.</p>
    <RouterLink to="/">Back to home</RouterLink>
  </main>
</template>
```

- [ ] **Step 2: Register catch-all route last**

In `apps/web/src/router/index.ts`, import `NotFoundView` and append this route **after** all other routes:

```ts
import NotFoundView from '../views/NotFoundView.vue'

// inside routes array, as the last entry:
{
  path: '/:pathMatch(.*)*',
  name: 'not-found',
  component: NotFoundView,
}
```

Do not remove create-vue sample routes in this task.

- [ ] **Step 3: Verify build still passes**

```powershell
cd C:\Users\User\SolaraX\apps\web
npm run build
```

Expected: exit 0.

- [ ] **Step 4: Manual 404 check (dev server)**

```powershell
cd C:\Users\User\SolaraX\apps\web
npm run dev
```

Open `http://localhost:5173/this-route-does-not-exist` (port may differ; use the URL Vite prints). Expected: “Page not found” and a link home. Stop the server with Ctrl+C.

- [ ] **Step 5: Commit**

```powershell
cd C:\Users\User\SolaraX
git add apps/web/src/views/NotFoundView.vue apps/web/src/router/index.ts
git commit -m "feat: add catch-all 404 route for the Vue SPA"
```

---

### Task 5: Env example + root README

**Files:**
- Create: `apps/web/.env.example`
- Modify: `README.md`
- Optional commit: staged design spec if still uncommitted: `docs/superpowers/specs/2026-08-15-vue-frontend-setup-design.md`

**Interfaces:**
- Consumes: none
- Produces: documented `VITE_API_BASE_URL` for future FastAPI client

- [ ] **Step 1: Add `.env.example`**

Create `apps/web/.env.example`:

```env
# Base URL for the FastAPI backend (no trailing slash)
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Ensure `.gitignore` in `apps/web` ignores `.env` / `.env.local` / `.env.*.local` (create-vue default). Do **not** commit real secrets.

- [ ] **Step 2: Update root `README.md`**

Replace `README.md` contents with:

```markdown
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
```

- [ ] **Step 3: Lint check**

```powershell
cd C:\Users\User\SolaraX\apps\web
npm run lint
```

Expected: exit 0 (fix any new lint issues introduced by Tasks 3–4 before continuing).

- [ ] **Step 4: Commit docs and env example**

```powershell
cd C:\Users\User\SolaraX
git add apps/web/.env.example README.md
git add docs/superpowers/specs/2026-08-15-vue-frontend-setup-design.md 2>$null
git add docs/superpowers/plans/2026-08-15-vue-frontend-setup.md 2>$null
git commit -m "docs: add web setup README, env example, and frontend plan"
```

---

### Task 6: Final verification gate

**Files:**
- Modify: none (verification only)

**Interfaces:**
- Consumes: Tasks 1–5 deliverables
- Produces: confirmation that success criteria from the spec are met

- [ ] **Step 1: Run full unit suite**

```powershell
cd C:\Users\User\SolaraX\apps\web
npm run test:unit -- --run
```

Expected: all tests PASS.

- [ ] **Step 2: Run lint + build**

```powershell
cd C:\Users\User\SolaraX\apps\web
npm run lint
npm run build
```

Expected: both exit 0.

- [ ] **Step 3: Confirm success criteria checklist**

- [ ] `apps/web` exists and `npm run dev` starts
- [ ] TypeScript, Router, Pinia, ESLint, Prettier, Vitest enabled
- [ ] Folders `composables/`, `services/`, `types/`, `layouts/` present
- [ ] Root README documents `apps/web` setup
- [ ] No ECharts/Leaflet/FastAPI code added

- [ ] **Step 4: No further commit required unless verification forced fixes**

If fixes were needed, commit them with a clear message, e.g. `fix: resolve lint issues after Vue scaffold`.

---

## Spec coverage (self-review)

| Spec requirement | Task |
|------------------|------|
| `create-vue` into `apps/web` | Task 1 |
| TS + Router + Pinia + Vitest + ESLint + Prettier | Task 1 |
| npm | Global + Task 1 |
| Folder conventions | Task 2 |
| Path alias `@/` | Task 2 |
| API errors in `services/` | Task 3 |
| Catch-all 404 | Task 4 |
| `VITE_*` env | Task 5 |
| Root README | Task 5 |
| Smoke: test / build / lint / dev | Tasks 1, 4, 6 |
| Defer ECharts/Leaflet/backend | Global Constraints |

**Deferred intentionally (spec):** Vue DevTools 7 interactive option — not available as a stable create-vue 3.23 flag; optional later via Vite plugin if desired.
