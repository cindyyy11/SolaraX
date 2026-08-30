# Guided 3D Inspection and CV Verification Implementation Plan

## Phase 1 — Typed inspection routes

1. Add route, waypoint, scene-configuration, building-variant, and inspection-mode types.
2. Map every supported scenario to a distinct route, camera target, visual treatment, and operator instruction.
3. Add pure route helpers and unit tests for scenario coverage, waypoint order, reset, and bounds.

## Phase 2 — Lazy Three.js scene

1. Add Three.js as a direct web dependency and isolate it behind an async Vue component.
2. Build procedural warehouse, commercial-roof, and ground-array geometry without claiming measured layout.
3. Render panels, inverters, energy paths, drone, route, waypoints, and scenario-specific affected regions.
4. Add adaptive pixel ratio, visibility pause, resize handling, disposal, loading, error, and CSS fallback states.

## Phase 3 — Guided inspection controls

1. Add Operational/Interactive 3D view switching, Baseline/Scenario comparison, play, pause, previous, next, reset, and selectable waypoints.
2. Animate the drone along scenario-specific segments and synchronize camera focus and operator instruction.
3. Connect severity to affected area and treatment intensity in both renderers.
4. Keep direct orbit, zoom, waypoint, and camera navigation available in Interactive 3D without a separate Explore mode.
5. Add reduced-motion, keyboard, touch, and readable non-3D equivalents.

## Phase 4 — CV verification workspace

1. Recompose evidence intake around the dispatch-verification question.
2. Add original/analysed/split viewing modes and synchronized finding selection.
3. Add explicit supports, verify, and does-not-support decisions with immutable dispatch state.
4. Add typed optional spatial-focus handoff and illustrative-placement disclosure when coordinates are absent.
5. Cover rejected, unavailable, low-confidence, conflicting, retry, and reset states.

## Phase 5 — Verification

1. Run type-check, route and component tests, lint, production build, and the Impeccable detector.
2. Verify desktop, tablet, mobile, keyboard, reduced motion, WebGL failure, and constrained-device fallback.
3. Confirm every scenario has a distinct route and visible state and no unsupported physical claim is introduced.

## Delivery order

Typed routes → lazy scene → guided controls → CV verification → bounded visual QA.

The existing CSS simulation remains usable throughout implementation and is never removed as a fallback.
