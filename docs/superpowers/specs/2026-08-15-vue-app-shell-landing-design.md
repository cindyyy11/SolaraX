# SolaraX Vue App Shell & Landing Design

**Date:** 2026-08-15  
**Status:** Approved (conversation) — pending user review of this written spec  
**Scope:** Replace create-vue sample UI with SolaraX marketing shell + landing + app placeholder  
**Depends on:** `docs/superpowers/specs/2026-08-15-vue-frontend-setup-design.md`

## Goal

Turn `apps/web` from the default Vue welcome pages into a brand-first SolaraX app shell: shared layout/nav, a daylight landing page that states the product job (detect solar sites and analyze performance), and a `/app` coming-soon placeholder for the future map/analytics workspace.

## Decisions Locked

| Topic | Choice |
|--------|--------|
| Slice | App shell (not FastAPI / API client this round) |
| Home type | Landing / product intro |
| Routes | `/` + `/app` placeholder + existing 404 |
| Visual direction | Solar daylight |
| Product one-liner job | Both: detect sites from imagery and turn them into performance insight |
| Architecture | Approach A — `DefaultLayout` + lean routes |

## Approach

**Chosen: Approach A — Shared marketing layout + lean routes**

- `DefaultLayout` owns top nav and wraps page content via `<RouterView />`.
- `App.vue` stays thin: it renders only `<DefaultLayout />` (Pinia/Router already mounted in `main.ts`).
- Avoid stuffing chrome only into `App.vue` without a layout component (Approach B).
- Avoid a multi-section marketing site (Approach C) until data/maps exist.

## Information Architecture

| Path | Route name | View | Purpose |
|------|------------|------|---------|
| `/` | `home` | `HomeView.vue` | Brand-first landing |
| `/app` | `app` | `AppComingSoonView.vue` | Coming-soon app entry |
| `/:pathMatch(.*)*` | `not-found` | `NotFoundView.vue` | Keep existing 404 |

**Remove:** create-vue About route/view, `HelloWorld`, welcome/icon sample components, and other unused scaffold UI. Remove unused Pinia `counter` store and its demos if nothing references them after cleanup.

## File Structure

```text
apps/web/src/
├── layouts/
│   └── DefaultLayout.vue      # wordmark + nav + slot/RouterView
├── views/
│   ├── HomeView.vue           # landing (rewrite)
│   ├── AppComingSoonView.vue  # placeholder
│   └── NotFoundView.vue       # keep; restyle lightly to match tokens if needed
├── assets/                    # tokens CSS and any hero imagery
├── App.vue                    # thin shell using DefaultLayout
├── router/index.ts            # /, /app, catch-all
└── (delete sample components under components/ as unused)
```

## Landing (Home) — Content & Composition

**First viewport (hero only):**

- Brand: **SolaraX** as hero-level signal (must remain strong if nav were removed).
- One headline (locked intent): *See solar sites. Know what they can deliver.*
- One supporting sentence: detect sites from imagery and turn them into performance insight.
- CTA group: primary `RouterLink` to `/app` labeled **Open app**. Secondary CTA optional; skip if it adds clutter.
- Dominant visual: full-bleed solar/atmosphere plane (CSS gradient and/or background image). No inset media cards, no floating badges, no stats strips, no feature grids in the hero.

**Chrome:**

- Slim top nav: SolaraX wordmark | Home | App.
- Active route styling via Vue Router link classes.

## `/app` — Coming Soon

- Same `DefaultLayout`.
- Short message that the workspace (map + analytics) is next.
- Link back to Home.
- No fake dashboard panels, charts, or map stubs.

## Visual System

**Direction:** Solar daylight — bright sky feeling, soft amber/gold accents.

**Rules:**

- Define CSS variables for color, type, spacing (e.g. in `assets` or global CSS).
- Expressive display font + readable body font; avoid default stacks (Inter, Roboto, Arial, system-only).
- Do **not** use purple-on-white / purple-indigo themes, warm cream + terracotta serif broadsheet, or heavy dark-console chrome for this landing.
- No card-heavy hero; cards only if later needed for interaction (not this round).

**Motion (2–3 intentional):**

1. Nav / link hover feedback.
2. Hero text or CTA entrance (fade/rise).
3. Optional soft background atmosphere shift — no particle spam.

## Responsive Behavior

- Mobile: hero remains one composition; brand + headline + support + CTA readable; nav usable (wrap or compact row).
- Desktop: full-bleed hero with brand dominance retained.

## Coding Practices

- Composition API + `<script setup lang="ts">` only.
- Views = routes; layout = chrome; no API calls in this round.
- Keep `@/` imports; reuse existing NotFound pattern.
- Env / FastAPI / ECharts / Leaflet remain out of scope.

## Testing & Verification

- `npm run lint`, `npm run test:unit -- --run`, `npm run build` pass after cleanup.
- Manual: `/` shows SolaraX landing; `/app` shows coming soon; unknown path still 404; primary CTA navigates to `/app`.
- No new E2E suite this round.

## Out of Scope

FastAPI, API client wiring, auth, Leaflet, ECharts, real map/dashboard UI, Supabase, CV/ML pipelines, multi-page marketing (features / pricing / blog).

## Success Criteria

1. Sample Vue welcome UI is gone; SolaraX brand leads the first viewport.
2. `DefaultLayout` provides consistent nav across Home, App placeholder, and 404 (404 may stay minimal but should not resurrect Vue logo sample chrome).
3. Routes `/`, `/app`, and catch-all work.
4. Daylight visual tokens are in place; lint/tests/build pass.
5. No charts/maps/backend dependencies added.
