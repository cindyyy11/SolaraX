# SolaraX Scenario Studio and Computer Vision Implementation Plan

## Goal

Implement the approved Scenario Studio, evidence-faithful 3D scenarios, computer-vision evidence workspace, and coordinated Operator/Scenario/Presentation visual modes without changing the measured dispatch artifact or overstating physical-site accuracy.

## Phase 1 — Typed scenario foundation

1. Add typed scenario definitions, parameter bounds, evidence-level metadata, response options, and pure calculation functions.
2. Implement scenario groups for revenue loss, inspection/safety, and grid/environment.
3. Derive outputs from existing expected-versus-actual and economics data where possible; mark bounded assumptions as simulated.
4. Add scenario store/composable with baseline snapshot, apply, reset, and serialization for shareable state.
5. Add unit tests for bounds, zero-state reset, non-negative generation/risk, evidence labels, and economic arithmetic.

## Phase 2 — Scenario Lab UX

1. Build the scenario selector with progressive disclosure by group.
2. Add severity and duration controls with visible units, bounds, and helper text.
3. Add before/after metric comparison for generation, RM exposure, confidence, and recommended response.
4. Add assumptions and evidence-level panel beside the outputs.
5. Add reset, unavailable-input, and conflicting-signal states.
6. Preserve keyboard operation, 44px targets, reduced motion, and mobile single-column flow.

## Phase 3 — 3D scenario integration

1. Extend the lightweight site simulation with equipment layers, panel-group states, energy-flow changes, bounded anomaly overlays, and scenario camera presets.
2. Keep fleet WebGL lazy-loaded and preserve 2D fallback.
3. Connect selected scenario regions to inferred/simulated labels; never imply measured geometry.
4. Add interruptible Presentation Mode replay using existing motion tokens and pause behavior when hidden.
5. Add accessible scene summaries and a readable tabular equivalent for every scenario output.

## Phase 4 — Computer-vision evidence workspace

1. Refactor `VisionEvidence.vue` into explicit idle, selected, validating, uploading, analysing, result, rejected, conflict, and unavailable states.
2. Add drag/drop, file chooser, and mobile camera capture with file type, size, resolution, and image-quality validation.
3. Add object URL lifecycle cleanup and an image preview/replacement action.
4. Add progress stages and cancellable/retryable request handling without blocking the page.
5. Add annotated-result presentation, confidence bands, model metadata, inference mode, timestamp, and review status.
6. Add side-by-side electrical/thermal context and action states: supports dispatch, needs field verification, or insufficient evidence.
7. Add optional “Show in 3D” handoff with explicit inferred/simulated placement labels.
8. Attach confirmed/unverified CV evidence to work-order context without mutating dispatch ranking.
9. Add component and service tests for validation, unknown-class handling, failed requests, reset, and evidence immutability.

## Phase 5 — Whole-system visual direction

1. Audit repeated card patterns, raw color usage, typography hierarchy, and layout repetition across Dispatch, Fleet Health, Site Detail, and Work Order.
2. Keep Operator Mode warm/editorial and readable; introduce Scenario Lab and Presentation Mode tonal surfaces through shared semantic tokens.
3. Select a distinctive display face only if self-hosting/licensing and bundle-size checks pass; preserve readable data typography and tabular numerals.
4. Replace generic visual repetition with intentional asymmetric composition, authored equipment linework, and clearer section rhythm.
5. Keep status colors reserved for operational meaning and remove decorative continuous animation.
6. Verify both themes, mobile widths, landscape/tablet widths, keyboard focus, and reduced motion.

## Phase 6 — Verification

1. Run type-check, unit tests, targeted lint, production build, and the Impeccable detector.
2. Test scenario calculations against fixture sites and verify reset returns the exact measured baseline.
3. Test vision idle/upload/result/error/conflict/unavailable states with a mocked service.
4. Test 3D-to-table parity, WebGL fallback, URL state, and work-order handoff.
5. Capture one bounded desktop/mobile visual QA batch and make one consolidated correction pass.
6. Confirm no unsupported physical geometry, customer, deployment, or autonomous-drone claims appear in UI or copy.

## Delivery order

Scenario foundation → Scenario Lab → CV workspace → 3D integration → whole-system visual pass → verification.

The existing dispatch workflow stays shippable after every phase. No phase may require a live CV service or WebGL for the core operator path.

