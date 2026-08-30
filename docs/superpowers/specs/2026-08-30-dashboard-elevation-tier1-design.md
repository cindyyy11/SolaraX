# Dashboard Elevation — Tier 1 (Foundation & Consistency)

## Goal

The dashboard has four screens built at different times by different people, each hand-rolling
the same handful of patterns slightly differently: three near-identical `.screen` container
rules, three different primary-CTA treatments, two different nav active-state treatments, and no
shared spacing, breakpoint, or z-index convention anywhere in `theme.css`. None of this is a bug
a user would file — it reads as "not quite premium" rather than "broken." This pass removes the
seams by extracting the two genuinely-shared patterns into one place and naming the values that
already exist as an implicit (undocumented, inconsistently-hit) convention.

This is **Tier 1** of a larger elevation backlog (survey: `apps/web/src` UI/UX audit, 30 Aug 2026)
— foundation and consistency only. Per-screen content restructuring (Site Detail's bolted-together
sections, Work Order's cramped micro-visualizations) and new entrance motion are explicitly
deferred to a later pass, not silently dropped.

## Non-goals

- No new library, no Tailwind, no font or icon swap — stays inside Vue 3 + scoped CSS + the
  existing `@lucide/vue`/Inter/Instrument Sans system, per CLAUDE.md's locked stack.
- No touching `SiteDigitalTwin.vue` or `FleetSkyline3D.vue`'s internal styling or stacking — both
  are the user's own recent, separate work, and their internal z-index/motion choices are
  local-stacking-context concerns this pass explicitly does not unify against page-level chrome.
- No retrofitting the new breakpoint convention across all 29 existing `@media` queries app-wide —
  applied to the specific files this pass touches; the rest is a documented follow-up, not a claim
  of completion.
- No renumbering existing z-index values — the z-index tokens **name the current numbers**
  (`--z-nav: 40` etc.) rather than changing behavior, so this pass carries no stacking-order risk.
- No mass rewrite of every hand-picked spacing value in every file — the spacing scale is defined
  and used in the specific consistency fixes below (container primitive, CTA unification); it is
  not retrofitted across all existing margins/paddings in this pass.

## Architecture

Two new global (unscoped) stylesheets join the existing pair (`fonts.css`, `theme.css`), loaded
in `main.ts` the same way:

- **`theme.css`** gains three new token groups (spacing, container widths, z-index) plus a
  documented-but-unenforced breakpoint comment. No existing token changes value.
- **`assets/layout.css`** (new) holds the two extracted shared primitives: the `.screen` container
  class with width modifiers, and the unified primary-CTA class. This mirrors why `NoticeCallout`
  and `DataStatusBadge` exist as extracted components — the codebase's own established response to
  the same kind of drift.

Each view keeps its own `<style scoped>` block for everything specific to that screen; only the
two primitives that were already byte-for-byte (or near-identical) duplicated across files move
out.

## Design

### 1. New tokens in `theme.css`

```css
/* Spacing — 4px rhythm, extends the existing --icon-xs/sm/md/lg naming precedent */
--space-3xs: 0.25rem;  /* 4px */
--space-2xs: 0.5rem;   /* 8px */
--space-xs: 0.75rem;   /* 12px */
--space-sm: 1rem;      /* 16px */
--space-md: 1.5rem;    /* 24px */
--space-lg: 2rem;      /* 32px */
--space-xl: 2.75rem;   /* 44px */
--space-2xl: 4rem;     /* 64px */

/* Container widths — the three widths already in use, named. Width varies by
   screen content (Dispatch's map+queue genuinely needs more room than Work
   Order's printable card) — this does not force one width on every screen,
   it stops each screen re-declaring its own copy of the same trio of rules. */
--container-narrow: 1100px;   /* Work Order — a single printable card */
--container-standard: 1380px; /* Site Detail, Fleet Health */
--container-wide: 1600px;     /* Dispatch — map + queue workspace */

/* z-index — names the CURRENT values, changes none of them. Scoped to
   page-level chrome only. Leaflet (FleetMap), deck.gl (FleetSkyline3D) and
   the CSS-3D scene (SiteDigitalTwin) manage their own internal stacking
   contexts for library reasons and are NOT part of this scale — do not
   compare their internal z-index values against these tokens. */
--z-nav: 40;         /* .app-rail, .mobile-header */
--z-fab: 35;         /* DemoGuide launch button */
--z-overlay: 50;     /* DemoGuide open panel */
--z-skip-link: 1000; /* .skip-link — must always win */
```

A comment documents the breakpoint convention this pass follows without introducing enforcement
CSS can't provide (custom properties don't work inside `@media`):

```css
/* Breakpoint convention (documented, not enforced — @media can't read custom
   properties). Recorded now, as part of the foundation pass, for future work
   to follow — Tier 1 itself adds no new @media query (the container/CTA
   extraction and nav fixes below don't need one). The 29 pre-existing
   @media queries elsewhere keep their current values until a future pass
   touches them.
     640px  — small / mobile-large
     900px  — tablet (already the dominant existing value: FleetMap,
              FleetSkyline3D, PerformanceModel, SiteDigitalTwin, and the
              Fleet Health cohort-panel grid from the previous session)
     1200px — wide desktop */
```

### 2. `assets/layout.css` (new file)

```css
/* Shared page-shell container. Three of four screens already declare this
   exact rule verbatim; Dispatch's .command differs only in using width:min()
   (it also carries outline:none as a focus target, which stays local to
   DispatchView — this primitive owns layout only, not focus behavior). */
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

/* Unified primary CTA. Combines the best-of-three from the current split:
   DispatchView.primary-action's glow shadow + press-scale (the most
   polished of the three existing treatments) with the icon-translate hover
   from SiteDetailView.work-order-link / WorkOrderView's print/save buttons. */
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

**Call sites** (view-side changes only — the class definitions above are the only new CSS):

- `DispatchView.vue` — root `.command` element additionally gets `screen screen--wide`; the
  `.command` rule in its own `<style scoped>` drops `width: min(100%, 1600px); margin: 0 auto;
  padding: clamp(...)` (now inherited from `.screen`/`.screen--wide`) and keeps only
  `outline: none` and anything else genuinely DispatchView-specific. `.primary-action` on the
  CTA element becomes `btn-primary`; the view's own `.primary-action` rule (including its mobile
  `width: 100%` override and reduced-motion override) is deleted since `.btn-primary` now owns
  that behavior — the reduced-motion carve-out moves into the shared class as shown above.
- `SiteDetailView.vue` — root `.screen` element becomes `screen` (no modifier — 1380px is the
  default); its own `.screen` rule is deleted. `.work-order-link` becomes `btn-primary`; the view's
  own `.work-order-link` rule is deleted (the icon-translate-on-hover behavior it introduced is
  preserved because `.btn-primary` includes it).
- `FleetHealthView.vue` — root `.screen` element becomes `screen`; its own `.screen` rule is
  deleted (this session's own recent addition, so this is a same-day cleanup, not a stale hangover).
- `WorkOrderView.vue` — root `.screen` element becomes `screen screen--narrow`; its own `.screen`
  rule is deleted. `.print-button`/`.save-button` become `btn-primary` (plus each keeps its own
  `margin-left` rule, which is layout placement, not the button's visual idiom, so it stays local).

### 3. Nav fixes in `App.vue`

- **Distinct landmark labels.** The `<aside>` keeps `aria-label="Primary navigation"` (it's the
  complete rail: brand, nav links, search, theme toggle). The inner `<nav class="app-rail__nav">`
  gains `aria-label="Site sections"` (it's the two-link navigation specifically, nested inside the
  aside). The mobile `<nav class="mobile-header__nav">` keeps `aria-label="Primary navigation"` to
  match the aside it stands in for at that viewport — the two "Primary navigation" labels never
  coexist in a real browser (`.mobile-header { display: none }` outside the `760px` breakpoint
  removes it from the accessibility tree), but giving the *desktop* nested `<nav>` a distinct label
  removes the confusing pair of identically-named landmarks a reader of the source — or a future
  screen-reader user in some edge case this pass hasn't considered — would otherwise hit.
- **Unified active-state pattern**, each surface using its own appropriate tokens rather than one
  surface's tokens forced onto the other:
  - Desktop `.app-rail__link.router-link-exact-active` — unchanged (already correct): tinted
    background (`--nav-active`), border (`--nav-active-border`), text (`--nav-active-text`) — all
    tuned against the dark `--nav-surface`.
  - Mobile `.mobile-header__nav a.router-link-exact-active` — currently a flat `--surface-2` fill
    with no border, a different visual idiom for the same "you are here" meaning. Changes to the
    same tinted-background-plus-border pattern using tokens already tuned for a light surface:
    `background: var(--surface-selected)` (the existing light amber-tinted surface token),
    `border-color`/`color: var(--action-text)` (the existing WCAG-passing amber-on-light token).

### 4. `FleetMap.vue` comment fix

Line 444's comment claims the app nav sits at z-index 20 and promises "see the z-index note in
theme.css" — a note that doesn't exist yet. Corrected to name the actual token:

```css
/* Above Leaflet's own panes (400) and controls (800). This value only
   competes with the app-rail (--z-nav, theme.css) if the map's own container
   fails to establish a stacking context of its own — verify before treating
   900 vs. --z-nav as directly comparable. */
```

## Testing

- `npm run build` after each file's edits — confirms no scoped-CSS selector went stale and no
  Vue template reference to a removed class was missed.
- Manual pass in a browser across all four screens at desktop and the `760px`/`430px` mobile
  breakpoints already in `App.vue`: confirm container widths are visually unchanged (this pass
  renames values, it does not change any of them — a visual diff would mean a mistake), confirm
  all four CTA buttons (Dispatch's primary action, Site Detail's work-order link, Work Order's
  print and save buttons) render identically to their current appearance, confirm mobile nav's
  active state now shows a tinted background + border instead of the flat fill.
- Accessibility tree check (`read_page` with default filter, i.e. visible elements only — not
  `filter: "all"`, which was this session's own false-positive source) at both a desktop and a
  760px-emulated viewport, confirming exactly one "Primary navigation"-equivalent landmark is
  present at each.
