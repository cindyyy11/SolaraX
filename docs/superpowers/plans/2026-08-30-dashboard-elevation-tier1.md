# Dashboard Elevation Tier 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the visible seams between SolaraX's four dashboard screens — three duplicated container rules, three different primary-CTA treatments, two nav active-state treatments, and no documented spacing/z-index convention — by extracting the two genuinely-shared patterns and naming the values that already exist as an implicit, inconsistently-hit convention.

**Architecture:** Two new token groups (spacing, container widths, z-index — naming current values, changing none) land in the existing `theme.css`. A new unscoped `assets/layout.css` (loaded in `main.ts` next to `theme.css`/`fonts.css`, the same way those already work) holds the one `.screen` container primitive and one `.btn-primary` CTA class. Each of the four views then points at these instead of re-declaring its own copy, and trims what becomes dead local CSS. `App.vue` gets two small, behavior-narrow nav fixes. `FleetMap.vue` gets one stale-comment correction.

**Tech Stack:** Vue 3 `<script setup lang="ts">`, plain scoped CSS + CSS custom properties (no Tailwind, no preprocessor), Vite build for type-checking.

**Spec:** `docs/superpowers/specs/2026-08-30-dashboard-elevation-tier1-design.md`

## Global Constraints

- No new library, no Tailwind, no font/icon swap — stays inside the existing Vue 3 + scoped CSS + `@lucide/vue` + Inter/Instrument Sans system.
- Do not touch `SiteDigitalTwin.vue` or `FleetSkyline3D.vue` internals — out of scope, the user's own recent separate work.
- Do not add or change any `@media` query beyond what's explicitly listed in a task below — no retrofitting the 29 pre-existing breakpoints app-wide.
- Z-index tokens **name the current numbers** — `--z-nav: 40`, `--z-fab: 35`, `--z-overlay: 50`, `--z-skip-link: 1000`. No z-index value anywhere changes.
- Container width values do not change (1600/1380/1100px stay exactly as they are) — only where they're declared changes.
- Every task ends with `npm run build` passing cleanly (from `apps/web/`) — this is the only automated check available, since this is CSS/markup-only work in a codebase with no component-mount test layer (confirmed precedent: `components/fleetBasemap.spec.ts` and `services/api.spec.ts` test pure `.ts` logic only, never a rendered `.vue` component).
- Commit after every task, using the exact commit message given in that task's last step.

---

### Task 1: Spacing, container-width, and z-index tokens in `theme.css`

**Files:**
- Modify: `apps/web/src/assets/theme.css`

**Interfaces:**
- Produces: `--space-3xs` through `--space-2xl`, `--container-narrow`/`--container-standard`/`--container-wide`, `--z-nav`/`--z-fab`/`--z-overlay`/`--z-skip-link` — all consumed by Tasks 2, 3, 4, 5, 6.

- [ ] **Step 1: Add the token block**

In `apps/web/src/assets/theme.css`, find this existing block (immediately before the closing `}` of `:root`):

```css
  /* Type — see fonts.css for why these two faces and why they are self-hosted.
     The fallback stacks are chosen to be metrically close so the one reflow
     when the webfont lands is small rather than a visible jump. */
  --font-sans: 'Inter Variable', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-display: 'Instrument Sans Variable', 'Inter Variable', system-ui, sans-serif;
}
```

Replace it with (adds the new token groups directly above the closing brace):

```css
  /* Type — see fonts.css for why these two faces and why they are self-hosted.
     The fallback stacks are chosen to be metrically close so the one reflow
     when the webfont lands is small rather than a visible jump. */
  --font-sans: 'Inter Variable', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-display: 'Instrument Sans Variable', 'Inter Variable', system-ui, sans-serif;

  /* Spacing — 4px rhythm, extends the --icon-xs/sm/md/lg naming precedent
     above. Not retrofitted across every existing margin/padding in this
     pass — used by the shared primitives in assets/layout.css and any new
     spacing this pass adds. */
  --space-3xs: 0.25rem;  /* 4px */
  --space-2xs: 0.5rem;   /* 8px */
  --space-xs: 0.75rem;   /* 12px */
  --space-sm: 1rem;      /* 16px */
  --space-md: 1.5rem;    /* 24px */
  --space-lg: 2rem;      /* 32px */
  --space-xl: 2.75rem;   /* 44px */
  --space-2xl: 4rem;     /* 64px */

  /* Container widths — the three widths already in use across the app,
     named. Width varies by screen content on purpose (Dispatch's map+queue
     genuinely needs more room than Work Order's printable card) — these
     tokens don't force one width everywhere, they stop each screen
     re-declaring its own copy of the same rule. */
  --container-narrow: 1100px;   /* Work Order — a single printable card */
  --container-standard: 1380px; /* Site Detail, Fleet Health */
  --container-wide: 1600px;     /* Dispatch — map + queue workspace */

  /* z-index — names the CURRENT values used elsewhere in the app; changes
     none of them. Scoped to page-level chrome only. Leaflet (FleetMap),
     deck.gl (FleetSkyline3D) and the CSS-3D scene (SiteDigitalTwin) manage
     their own internal stacking contexts for library reasons and are NOT
     part of this scale — do not compare their internal z-index values
     against these tokens. */
  --z-nav: 40;         /* .app-rail, .mobile-header */
  --z-fab: 35;         /* DemoGuide launch button */
  --z-overlay: 50;     /* DemoGuide open panel */
  --z-skip-link: 1000; /* .skip-link — must always win */

  /* Breakpoint convention (documented, not enforced — @media can't read
     custom properties). Recorded now, as part of this foundation pass, for
     future work to follow — this pass itself adds no new @media query. The
     29 pre-existing @media queries elsewhere keep their current values
     until a future pass touches them.
       640px  — small / mobile-large
       900px  — tablet (already the dominant existing value: FleetMap,
                FleetSkyline3D, PerformanceModel, SiteDigitalTwin, and the
                Fleet Health cohort-panel grid)
       1200px — wide desktop */
}
```

- [ ] **Step 2: Build**

Run (from `apps/web/`): `npm run build`
Expected: builds cleanly. Adding unused custom properties cannot break a build — this step exists to catch a stray typo (unbalanced brace, bad comment close) before it compounds in later tasks.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/assets/theme.css
git commit -m "feat(web): add spacing, container-width and z-index tokens"
```

---

### Task 2: `assets/layout.css` — shared container and CTA primitives

**Files:**
- Create: `apps/web/src/assets/layout.css`
- Modify: `apps/web/src/main.ts`

**Interfaces:**
- Consumes: `--container-narrow/standard/wide` (Task 1), and existing tokens `--radius-md`, `--action-fill`, `--action-fill-hover`, `--action-ink`, `--font-display`, `--duration-fast`, `--ease-out`.
- Produces: CSS classes `.screen`, `.screen--wide`, `.screen--narrow`, `.btn-primary` — consumed by Tasks 3, 4, 5, 6.

- [ ] **Step 1: Create the file**

Create `apps/web/src/assets/layout.css`:

```css
/**
 * SolaraX shared layout primitives — unscoped, loaded once in main.ts next
 * to theme.css/fonts.css, the same way those already work. Vue's
 * <style scoped> can't share a rule across components, so anything used
 * identically by more than one view belongs here instead of being
 * re-declared per file. Two primitives live here because they're the two
 * patterns Tier 1's audit found duplicated 3-4x across the app: the page
 * container shell, and the primary call-to-action button.
 */

/* Shared page-shell container. Three of four screens declared this exact
   rule verbatim before this pass; the fourth (Dispatch) differed only in
   using width:min() and carrying an unrelated outline:none for its own use
   as a focus target, which stays local to that view. */
.screen {
  max-width: var(--container-standard);
  margin: 0 auto;
  padding: clamp(1.25rem, 2.8vw, 2.75rem);
}
.screen--wide {
  max-width: var(--container-wide);
}
.screen--narrow {
  max-width: var(--container-narrow);
}

/* Unified primary CTA. Combines the best-of-three from three previously
   separate treatments: DispatchView's glow shadow + press-scale (the most
   polished of the three) with the icon-translate-on-hover from Site
   Detail's work-order link and Work Order's print/save buttons. */
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 48px;
  padding: 0 1.15rem;
  background: var(--action-fill);
  color: var(--action-ink);
  border: 0;
  border-radius: var(--radius-md);
  font: 700 0.83rem var(--font-display);
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
  box-shadow: 0 8px 22px color-mix(in srgb, var(--action-fill) 20%, transparent);
  transition:
    background-color var(--duration-fast) var(--ease-out),
    transform 120ms var(--ease-out);
}
.btn-primary:hover {
  background: var(--action-fill-hover);
}
.btn-primary:active {
  transform: scale(0.97);
}
.btn-primary svg {
  transition: transform var(--duration-fast) var(--ease-out);
}
.btn-primary:hover svg {
  transform: translateX(2px);
}
@media (prefers-reduced-motion: reduce) {
  .btn-primary:active {
    transform: none;
  }
}
```

- [ ] **Step 2: Load it in `main.ts`**

In `apps/web/src/main.ts`, change:

```ts
import './assets/fonts.css'
import './assets/theme.css'
```

to:

```ts
import './assets/fonts.css'
import './assets/theme.css'
import './assets/layout.css'
```

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: builds cleanly. `.screen`/`.btn-primary` are defined but not yet referenced by any template — this step confirms the new file itself is valid CSS and the import resolves.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/assets/layout.css apps/web/src/main.ts
git commit -m "feat(web): add shared .screen and .btn-primary layout primitives"
```

---

### Task 3: Adopt the primitives in `DispatchView.vue`

**Files:**
- Modify: `apps/web/src/views/DispatchView.vue`

**Interfaces:**
- Consumes: `.screen`, `.screen--wide`, `.btn-primary` (Task 2).

- [ ] **Step 1: Update the template**

Find:

```html
  <main id="main-content" class="command" tabindex="-1">
```

Replace with:

```html
  <main id="main-content" class="command screen screen--wide" tabindex="-1">
```

Find:

```html
          <button type="button" class="primary-action" @click="reviewPriorities">
            Review priorities <ArrowUpRight :size="17" aria-hidden="true" />
          </button>
```

Replace with:

```html
          <button type="button" class="btn-primary" @click="reviewPriorities">
            Review priorities <ArrowUpRight :size="17" aria-hidden="true" />
          </button>
```

- [ ] **Step 2: Trim the now-redundant local CSS**

Find, in the `<style scoped>` block:

```css
.command {
  width: min(100%, 1600px);
  margin: 0 auto;
  padding: clamp(1.25rem, 2.8vw, 2.75rem);
  outline: none;
}
```

Replace with (keeps only what `.screen`/`.screen--wide` don't already cover):

```css
.command {
  outline: none;
}
```

Find:

```css
.primary-action {
  display: inline-flex;
  min-height: 48px;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  padding: 0 1.15rem;
  background: var(--action-fill);
  color: var(--action-ink);
  border: 0;
  border-radius: var(--radius-md);
  font: 700 0.83rem var(--font-display);
  cursor: pointer;
  box-shadow: 0 8px 22px color-mix(in srgb, var(--action-fill) 20%, transparent);
  transition:
    background-color var(--duration-fast) var(--ease-out),
    transform 120ms var(--ease-out);
}
.primary-action:active {
  transform: scale(0.97);
}
```

Delete both rules entirely — `.btn-primary` now supplies this.

Find, inside the `@media (max-width: 760px)` block:

```css
  .primary-action {
    width: 100%;
  }
```

Replace with:

```css
  .btn-primary {
    width: 100%;
  }
```

Find, inside the `@media (prefers-reduced-motion: reduce)` block:

```css
  .primary-action:active {
    transform: none;
  }
```

Delete this rule — `.btn-primary`'s own reduced-motion carve-out (added in Task 2) now covers it. The `.load-state__pulse` rule in that same block stays untouched.

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: builds cleanly, no unresolved selector errors.

- [ ] **Step 4: Manual verification**

Run `npm run dev`, open `/`. Confirm: page width/margins look unchanged from before this task (this is a rename, not a resize), the "Review priorities" button still has its glow shadow, press-scale, and icon nudge on hover, and at a narrow viewport (≤760px) the button still goes full width.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/views/DispatchView.vue
git commit -m "refactor(web): adopt shared screen/btn-primary primitives in DispatchView"
```

---

### Task 4: Adopt the primitives in `SiteDetailView.vue`

**Files:**
- Modify: `apps/web/src/views/SiteDetailView.vue`

**Interfaces:**
- Consumes: `.screen`, `.btn-primary` (Task 2).

- [ ] **Step 1: Update the template**

Find:

```html
  <main class="screen">
```

This already matches `.screen`'s default (1380px = `--container-standard`) — no modifier class needed here.

Find the work-order link (its exact surrounding markup, to locate the `class` attribute):

```html
            :to="`/site/${site.site_id}/work-order`"
            class="work-order-link"
          >
```

Replace `class="work-order-link"` with:

```html
            class="btn-primary"
```

- [ ] **Step 2: Trim the now-redundant local CSS**

Find, in `<style scoped>`:

```css
.screen {
  max-width: 1380px;
  margin: 0 auto;
  padding: clamp(1.25rem, 2.8vw, 2.75rem);
}
```

Delete this rule entirely — the global `.screen` (Task 2) now supplies it.

Find:

```css
.work-order-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.9rem;
  background: var(--action-fill);
  color: var(--action-ink);
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
  transition:
    background-color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}

.work-order-link:hover {
  background: var(--action-fill-hover);
}

.work-order-link:active {
  transform: scale(0.97);
}

.work-order-link svg {
  transition: transform var(--duration-fast) var(--ease-out);
}

.work-order-link:hover svg {
  transform: translateX(2px);
}
```

Delete all six rules entirely — `.btn-primary` now supplies this.

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: builds cleanly.

- [ ] **Step 4: Manual verification**

Run `npm run dev`, open any `/site/:siteId` page. Confirm: page width/margins unchanged, the work-order button now shows the glow shadow and press-scale it didn't have before (this one visibly upgrades, unlike Task 3's identical-looking rename) while keeping its icon-nudge-on-hover.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/views/SiteDetailView.vue
git commit -m "refactor(web): adopt shared screen/btn-primary primitives in SiteDetailView"
```

---

### Task 5: Adopt the primitives in `FleetHealthView.vue`

**Files:**
- Modify: `apps/web/src/views/FleetHealthView.vue`

**Interfaces:**
- Consumes: `.screen` (Task 2). (Fleet Health has no primary-CTA button, so `.btn-primary` doesn't apply here.)

- [ ] **Step 1: Update the template**

Find:

```html
  <main class="screen">
```

Already matches `.screen`'s default (1380px) — no change needed to the template.

- [ ] **Step 2: Trim the now-redundant local CSS**

Find, in `<style scoped>`:

```css
.screen {
  max-width: 1380px;
  margin: 0 auto;
  padding: clamp(1.25rem, 2.8vw, 2.75rem);
}
```

Delete this rule entirely — the global `.screen` (Task 2) now supplies it. This is this session's own recently-added rule, so this is a same-day cleanup, not a stale hangover.

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: builds cleanly.

- [ ] **Step 4: Manual verification**

Run `npm run dev`, open `/fleet-health`. Confirm page width/margins are pixel-identical to before this task.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/views/FleetHealthView.vue
git commit -m "refactor(web): adopt shared .screen primitive in FleetHealthView"
```

---

### Task 6: Adopt the primitives in `WorkOrderView.vue`

**Files:**
- Modify: `apps/web/src/views/WorkOrderView.vue`

**Interfaces:**
- Consumes: `.screen`, `.screen--narrow`, `.btn-primary` (Task 2).

- [ ] **Step 1: Update the template**

Find:

```html
  <main class="screen">
```

Replace with:

```html
  <main class="screen screen--narrow">
```

Find:

```html
        <button type="button" class="print-button" @click="printCard">
          <Printer :size="15" aria-hidden="true" /> Print / export
```

Replace `class="print-button"` with:

```html
        <button type="button" class="btn-primary print-button" @click="printCard">
```

(Keep the rest of that line — the `<Printer>` icon and its `@click` handler — unchanged; only the `class` attribute value changes, to `btn-primary print-button` so the button gets the shared visual idiom while `.print-button` stays as a hook for the placement rule kept in Step 2.)

Find:

```html
            <button type="button" class="save-button" @click="saveFindings">Save findings</button>
```

Replace with:

```html
            <button type="button" class="btn-primary save-button" @click="saveFindings">Save findings</button>
```

- [ ] **Step 2: Trim the now-redundant local CSS, keep placement rules**

Find, in `<style scoped>`:

```css
.screen {
  max-width: 1100px;
  margin: 0 auto;
  padding: clamp(1.25rem, 2.8vw, 2.75rem);
}
```

Delete this rule entirely — the global `.screen`/`.screen--narrow` (Task 2) now supply it.

Find:

```css
.print-button,
.save-button {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-left: auto;
  padding: 0.5rem 0.9rem;
  background: var(--action-fill);
  color: var(--action-ink);
  border: none;
  border-radius: var(--radius-sm);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background-color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}

.print-button:hover,
.save-button:hover {
  background: var(--action-fill-hover);
}

.print-button:active,
.save-button:active {
  transform: scale(0.97);
}

.save-button {
  margin-left: 0;
}
```

Replace with (keeps only the placement rules `.btn-primary` doesn't own — each button's `margin-left`):

```css
.print-button {
  margin-left: auto;
}

.save-button {
  margin-left: 0;
}
```

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: builds cleanly.

- [ ] **Step 4: Manual verification**

Run `npm run dev`, open any `/site/:siteId/work-order` page. Confirm: page is visibly narrower than Dispatch/Site Detail/Fleet Health (1100px vs 1380/1600px — this was already true, just confirming the rename didn't change it), both "Print / export" and "Save findings" now show the glow shadow and press-scale, "Print / export" stays right-aligned and "Save findings" stays left-aligned within its own row.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/views/WorkOrderView.vue
git commit -m "refactor(web): adopt shared screen/btn-primary primitives in WorkOrderView"
```

---

### Task 7: Nav landmark label, active-state, and z-index token adoption in `App.vue`

**Files:**
- Modify: `apps/web/src/App.vue`

**Interfaces:**
- Consumes: existing tokens `--surface-selected`, `--action-text` (light-surface pair, for the mobile fix); `--nav-active`/`--nav-active-border`/`--nav-active-text` stay exactly as they are for desktop; `--z-nav`/`--z-skip-link` (Task 1).

- [ ] **Step 1: Adopt the z-index tokens (values unchanged, now named)**

Find:

```css
.skip-link {
  position: fixed;
  top: 0.75rem;
  left: 0.75rem;
  z-index: 1000;
```

Replace the `z-index` line with:

```css
  z-index: var(--z-skip-link);
```

Find:

```css
.app-rail {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 40;
```

Replace the `z-index` line with:

```css
  z-index: var(--z-nav);
```

Find (inside the `@media (max-width: 760px)` block):

```css
  .mobile-header {
    position: fixed;
    inset: 0 0 auto;
    z-index: 40;
```

Replace the `z-index` line with:

```css
    z-index: var(--z-nav);
```

- [ ] **Step 2: Give the desktop nested `<nav>` its own label**

Find:

```html
      <nav class="app-rail__nav">
```

Replace with:

```html
      <nav class="app-rail__nav" aria-label="Site sections">
```

(The outer `<aside aria-label="Primary navigation">` is unchanged — it remains the complete rail landmark: brand, nav links, search, theme toggle. This nested `<nav>` previously had no label of its own; giving it a distinct one removes the confusing pair of identically-named landmarks a reader of the source would otherwise hit, even though in a real browser only one of the desktop/mobile pair is ever in the accessibility tree at once via `.mobile-header { display: none }`.)

- [ ] **Step 3: Replace the mobile active-state rule with light-surface-safe tokens**

Find:

```css
  .mobile-header__nav a.router-link-exact-active {
    color: var(--text-primary);
    background: var(--surface-2);
  }
```

Replace with:

```css
  .mobile-header__nav a.router-link-exact-active {
    color: var(--action-text);
    background: var(--surface-selected);
    border-color: var(--action-text);
  }
```

Find the neighboring base rule it needs a transparent border to transition from:

```css
  .mobile-header__nav a {
    display: inline-flex;
    min-height: 2.75rem;
    align-items: center;
    padding: 0 0.65rem;
    color: var(--text-secondary);
    border-radius: var(--radius-md);
    font-size: 0.78rem;
    font-weight: 650;
    text-decoration: none;
  }
```

Replace with (adds a transparent border so the active state's border doesn't shift layout, matching how `.app-rail__link` already does this):

```css
  .mobile-header__nav a {
    display: inline-flex;
    min-height: 2.75rem;
    align-items: center;
    padding: 0 0.65rem;
    color: var(--text-secondary);
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    font-size: 0.78rem;
    font-weight: 650;
    text-decoration: none;
  }
```

- [ ] **Step 4: Build**

Run: `npm run build`
Expected: builds cleanly.

- [ ] **Step 5: Manual verification**

Run `npm run dev`. Confirm the skip-link (Tab from the top of the page) and rail still render and behave identically to before this task — this task renamed `z-index` values, it did not change any of them. At desktop width, confirm the rail's active-link styling is unchanged. At a viewport ≤760px (browser DevTools device toolbar, or resize), confirm the active nav link ("Dispatch" or "Fleet") now shows a light amber-tinted background with a matching border and amber text, instead of the previous flat gray fill.

- [ ] **Step 6: Accessibility check**

With the dev server running, use the browser's accessibility tree inspector (or an automated `read_page`-style tool) at desktop width with the **default/visible-only filter** (not an "include all elements" mode — that mode intentionally includes CSS-hidden elements and will show both navs regardless of correctness). Confirm exactly one landmark named "Primary navigation" is present, and the rail's inner nav now reads as "Site sections".

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/App.vue
git commit -m "fix(web): distinct nav landmark label, z-index tokens, light-surface mobile active-state"
```

---

### Task 8: `DemoGuide.vue` z-index token adoption + `FleetMap.vue` stale comment fix

**Files:**
- Modify: `apps/web/src/components/DemoGuide.vue`
- Modify: `apps/web/src/components/FleetMap.vue`

**Interfaces:**
- Consumes: `--z-fab`, `--z-overlay` (Task 1) in `DemoGuide.vue`. `FleetMap.vue`'s change is comment-only, no behavior, no CSS value change.

- [ ] **Step 1: Adopt the z-index tokens in `DemoGuide.vue` (values unchanged, now named)**

Find (the launch button's rule, around line 101):

```css
  position: fixed;
  right: 1.25rem;
  bottom: 1.25rem;
  z-index: 35;
```

Replace the `z-index` line with:

```css
  z-index: var(--z-fab);
```

Find (the open panel's rule, around line 119):

```css
  position: fixed;
  right: 1.25rem;
  bottom: 1.25rem;
  z-index: 50;
```

Replace the `z-index` line with:

```css
  z-index: var(--z-overlay);
```

- [ ] **Step 2: Fix the stale comment in `FleetMap.vue`**

Find (around line 444):

```css
/* Above Leaflet's own panes (400) and controls (800), below the app nav (20
   on a different stacking context) — see the z-index note in theme.css. */
```

Replace with:

```css
/* Above Leaflet's own panes (400) and controls (800). This value only
   competes with the app-rail (--z-nav, theme.css) if the map's own
   container fails to establish a stacking context of its own — verify
   before treating 900 vs. --z-nav as directly comparable. */
```

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: builds cleanly.

- [ ] **Step 4: Manual verification**

Run `npm run dev`, open `/`, open the `DemoGuide` FAB (bottom-right launch button). Confirm it still opens its panel above all other page content, exactly as before this task — this task renamed `z-index` values, it did not change any of them.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/DemoGuide.vue apps/web/src/components/FleetMap.vue
git commit -m "refactor(web): adopt z-index tokens in DemoGuide, correct stale FleetMap comment"
```

---

## Self-Review

**Spec coverage:**
1. Spacing/container/z-index tokens in `theme.css` — Task 1. ✅
2. `assets/layout.css` with `.screen`/`.btn-primary` — Task 2. ✅
3. `DispatchView.vue`, `SiteDetailView.vue`, `FleetHealthView.vue`, `WorkOrderView.vue` call-site updates — Tasks 3–6. ✅
4. `App.vue` nav landmark label + active-state fix — Task 7. ✅
5. `FleetMap.vue` stale comment fix, plus z-index token adoption at their real call sites (`App.vue`, `DemoGuide.vue`) — Tasks 7–8. ✅
6. Non-goals (no Tailwind/font/icon swap, no touching `SiteDigitalTwin`/`FleetSkyline3D`, no retrofitting all 29 `@media` queries, no z-index renumbering, no mass spacing rewrite) — none of the 8 tasks touch those files or change a numeric z-index/container value, only where each is declared. ✅

**Placeholder scan:** every step carries literal before/after code and exact commands; no TBDs.

**Type consistency:** `.screen`/`.screen--wide`/`.screen--narrow`/`.btn-primary` are defined once in Task 2 and referenced by the same names in Tasks 3–6 with no renaming drift. `--z-nav`/`--z-fab`/`--z-overlay`/`--z-skip-link` (Task 1) are substituted at all five of their real call sites — `App.vue`'s `.skip-link`/`.app-rail`/`.mobile-header` (Task 7) and `DemoGuide.vue`'s launch button/open panel (Task 8) — with the numeric value unchanged at every site. This was fixed during self-review: the first draft defined the tokens in Task 1 but never applied them anywhere, which would have repeated the exact "dead token" pattern the source spec's own survey flagged for the unused `--icon-xs/sm/md/lg` scale.
