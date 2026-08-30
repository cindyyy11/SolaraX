# SolaraX Mission Control Redesign — Implementation Plan

## Goal

Ship the approved operator-first mission-control interface while preserving the existing dispatch schema, claim discipline, and 2D/3D map behavior.

## Workstream 1 — Design system and application shell

1. Extend the semantic token system with mission-control surfaces, elevation, larger radii, and motion tokens while retaining reserved status colors.
2. Replace the narrow top navigation with a responsive application shell: desktop rail, compact mobile header, labelled destinations, accessible skip link, and theme control.
3. Preserve the existing official brand assets and lazy-loaded routes.

## Workstream 2 — Dispatch mission control

1. Refactor the dispatch landing screen into a command header, financial summary strip, 60/40 spatial-and-queue workspace, healthy fleet outcome, and provenance footer.
2. Preserve all existing selectors, threshold logic, source fallback, status grouping, and truthful empty states.
3. Synchronize map selection with the ranked queue and add a compact evidence preview without fabricating values.
4. Retain Map, Aerial, and lazy-loaded 3D modes and give the 3D mode enough space to function as the signature visual experience.
5. Provide a mobile Map/List switch instead of compressing both panels.

## Workstream 3 — Motion, responsive behavior, and accessibility

1. Use CSS transitions for frequent selection and hover feedback; keep them subtle and interruptible.
2. Use one occasional explanatory entrance for the command workspace and preserve the existing 3D elevation transition.
3. Respect reduced motion and coarse pointers.
4. Maintain keyboard navigation, labelled controls, visible focus, 44-pixel targets, semantic headings, and list/table alternatives to spatial data.

## Workstream 4 — Verification

1. Run formatting, type checking, unit tests, linting, and production build.
2. Run the Impeccable detector once over changed UI targets.
3. Inspect desktop and mobile renders in one batched visual QA pass.
4. Fix the consolidated findings and run one final confirmation pass.

