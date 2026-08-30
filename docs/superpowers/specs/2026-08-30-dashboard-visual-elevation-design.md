# Dashboard Visual Elevation

## Goal

Give SolaraX's four screens a felt "wow" — more attractive, more confident, easier to navigate —
without breaking the locked stack (Vue 3, scoped CSS, no Tailwind, existing Inter/Instrument Sans
fonts, `@lucide/vue` icons, navy+amber brand) or the print-document mechanics Work Order depends
on. This is a follow-up to the completed Tier 1 foundation pass (tokens, `.screen`/`.btn-primary`
primitives) — Tier 1 was intentionally near-invisible; this pass is not.

## Correction from the conversational proposal

The design presented and approved in chat characterized Site Detail as having "3 bolted-together
components" and Work Order as "one dense card." A fresh survey of the current files (both have
changed substantially from concurrent work during this session) shows neither is accurate:

- **Site Detail's 9 content blocks already each render their own card chrome** — the problem is
  drift between them, not bareness. 4 older components (`CohortChart`, `InverterPanel`,
  `InverterThermalMap`, `VisionEvidence`, all wrapped in a bare `.block`) use `--radius-md` with no
  shadow; `.panel` and 3 newer components (`SpatialOperations`, `EvidenceTimeline`,
  `SiteComparison`) use `--radius-lg` plus `--elevation-1`; and the two "dark instrument" cards
  (`PerformanceModel` using `--nav-surface`, `RecoveryTracker` using a hardcoded `#13211d`) don't
  even share a token with each other. Nine blocks, three different chrome recipes.
- **Work Order already has 9 numbered sections** (`.section` with a CSS counter) plus a rank chart,
  a sparkline, and two callouts — not an undifferentiated card. It is deliberately one continuous
  document with hairline dividers, because it prints (`@media print` rebuilds it as a repeating
  letterhead via `.print-doc { display: table }`, with `break-inside: avoid` on every block).
  Restructuring it into separate floating `--elevation-1` cards would look wrong on screen relative
  to its own print output and would fight the print mechanism this pass must not touch.

The underlying goals from the approved conversation — Site Detail reads as one coherent page, Work
Order breathes properly — are unchanged. The mechanism below is corrected to match reality.

## Non-goals

- No Tailwind, no font swap, no icon-library swap — same constraint as Tier 1.
- No change to `SiteDigitalTwin.vue` / `FleetSkyline3D.vue` internals, the Leaflet map, or the
  ECharts cohort chart's rendering logic — chrome/spacing around them only.
- No structural rewrite of Work Order's `.section`/`.print-doc` mechanism — every print-mode rule
  listed in the survey (`.no-print`, `@page`, `.print-doc`'s table-display trick, `break-inside:
  avoid`, `.signature`'s print-only display) must survive unchanged. New elevation/shadow added to
  `.card` or `.section` in the base ruleset is safe only if not also added inside `@media print`
  (which already zeroes `.card`'s box-shadow for print).
- No data/logic changes — pure visual, layout, and motion, same discipline as Tier 1.

## Design

### 1. Two new global card classes in `layout.css` — closing the drift

```css
.card {
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-lg);
  box-shadow: var(--elevation-1);
}
.card--dark {
  background: var(--nav-surface);
  border: 1px solid var(--nav-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--elevation-1);
}
.card--interactive {
  transition:
    transform var(--duration-base) var(--ease-out),
    box-shadow var(--duration-base) var(--ease-out);
}
.card--interactive:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 40px color-mix(in srgb, var(--brand-navy) 12%, transparent);
}
@media (prefers-reduced-motion: reduce) {
  .card--interactive:hover {
    transform: none;
  }
}
```

Every one of Site Detail's 9 content blocks adopts one of these two classes in place of its own
hand-rolled `background`/`border`/`border-radius`/`box-shadow` declarations:

- **`.card`** (light): `CohortChart`'s wrapper, `InverterPanel`, `InverterThermalMap`,
  `VisionEvidence` (all currently `--radius-md`, no shadow — gain both), `SpatialOperations`,
  `EvidenceTimeline` (currently missing elevation — gains it), `SiteComparison`, and
  `SiteDetailView.vue`'s own `.panel` rule (already matches `.card` exactly — pure de-duplication).
- **`.card--dark`** (the two instrument-panel cards): `PerformanceModel` and `RecoveryTracker`.
  `RecoveryTracker`'s hardcoded `#13211d` is replaced by `--nav-surface` (`#101b18`) — a small,
  deliberate, visible shift, not a no-op; its bespoke `0 18px 42px rgba(9,22,18,.16)` shadow is
  replaced by the shared `--elevation-1`, matching `PerformanceModel`.

This mirrors Tier 1's own methodology exactly: a repeated hand-rolled pattern gets one shared
definition, consumers adopt it, consistency stops depending on nine separate authors independently
getting the same four CSS properties right.

`.card--interactive` (the hover-lift) is added to all 9 of Site Detail's blocks — they're browsable
content, and a subtle lift reinforces the physical-card language. It is explicitly NOT added to
Work Order's `.card` — that element is a print-document root, not a browsable card, and "lifting"
on hover would read as a mistake on something meant to be read and printed as one continuous sheet.

### 2. Rhythm: first real use of Tier 1's `--space-*` tokens

Tier 1's final review flagged all 8 `--space-*` tokens as defined-but-unused. This pass gives them
a first real consumer: `SiteDetailView.vue` wraps its content flow (everything from the identity
header through the VisionEvidence block) in one `.page-stack { display: flex; flex-direction:
column; gap: var(--space-lg); }` container, replacing each block's own ad-hoc outer margin
(`1.5rem 0` on some, `1.75rem 0` on others) with one consistent value from the shared scale. Any
component that sets its own top/bottom margin on its root has that margin removed so it doesn't
double up with the wrapper's `gap`.

### 3. Typography confidence

Dispatch's H1 already uses a bold `clamp(2rem, 4vw, 3.7rem)` display scale. Site Detail's
`.head__name`, Fleet Health's `.head__title`, and Work Order's `.card__head` title are each bumped
to match that same confidence tier (exact clamp values set per screen's current size during
implementation, scaled up proportionally — this is a sizing/weight change only, not a new font).

### 4. Motion: shared entrance stagger

One new keyframe + utility class in `layout.css`:

```css
@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.stagger-in {
  animation: card-enter var(--duration-base) var(--ease-out) both;
}
@media (prefers-reduced-motion: reduce) {
  .stagger-in {
    animation: none;
  }
}
```

Applied with an inline `animation-delay` (30-50ms increments, computed from each item's index) to:
Dispatch's `.signal-strip` tiles and priority-queue cards, Fleet Health's `.tiles`/`.tiles--secondary`
tiles. This is the same technique already used for `FleetHealthView`'s Tier-1 skeleton shimmer and
several existing per-component keyframes (`pulse`, `demo-enter`, `model-enter`) — one shared version
instead of a ninth bespoke one.

### 5. Fleet Health's headline tiles get real dominance

`docs/Schema.md` §5 states outright: *"Give them visual weight on Screen 1 — they are not a
footnote."* Applied here to Fleet Health's two `tile--primary` tiles (trips avoided, saving): a
subtle `--surface-selected` background wash (the same light-amber-tinted token Tier 1 already used
for the mobile nav's active state) behind the two primary tiles, distinguishing them from the six
secondary tiles at a glance rather than relying on text color alone.

### 6. Work Order: rhythm polish, not restructuring

Within the existing 9-section, one-continuous-document structure: increase the vertical spacing
between `.section` blocks slightly for more breathing room (a `--space-*` token, not restructuring
into cards), give the `.section__title::before` counter a small visual treatment (a filled circle
badge instead of plain text, still exempt from `@media print`'s existing text-only footer/header
handling), and confirm `.rank`/`.trace` (which sit outside the counter, presenting evidence before
the numbered steps) visually integrate with the same spacing rhythm as the sections around them.

### 7. Nav rail: minor polish only

No structural change (Tier 1 already reviewed and fixed this file's real issues). Optional small
touch: `.card--interactive`'s hover-lift language extended to `.app-rail__link` for consistency, if
implementation time allows — explicitly lowest priority in this pass.

## Testing

- `npm run build` after every file's edits, same as Tier 1.
- Manual verification against a real browser at each of the 4 screens, both light and dark theme
  (several tokens this pass touches — `--surface-1`, `--nav-surface`, `--elevation-1` — carry
  distinct dark-mode values).
- **Work Order print verification is mandatory and specific**: open the browser print preview
  (or print-to-PDF) after this pass's changes and confirm the repeating letterhead header/footer
  still works, `.card`'s shadow is still suppressed in print output, and no new floating-card
  shadow appears on the printed page.
- Confirm `prefers-reduced-motion: reduce` disables both the new hover-lift and the new entrance
  stagger, consistent with every other animation already in this codebase.
