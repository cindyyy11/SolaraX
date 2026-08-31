# Closed-Loop Operations Intelligence Implementation Plan

## Phase 1 — Evidence and recovery foundation

1. Add typed evidence events, recovery states, intervention records, resilience categories, and source-status metadata.
2. Add pure recovery calculations for projected and verified kWh, RM, payback, confidence, and pending-data eligibility.
3. Add fixture-safe adapters from existing dispatch and work-order data without mutating source records.
4. Test arithmetic, immutability, missing telemetry, invalid windows, and evidence labels.

## Phase 2 — Recovery Tracker

1. Build fleet and site recovery summaries with pending, projected, and verified states.
2. Explain baseline window, observation window, tariff, confidence, and missing inputs.
3. Add pre/post performance comparison and cumulative value with truthful status labels.
4. Add responsive, keyboard, empty, and error states.

## Phase 3 — Intervention Optimizer

1. Add editable technician capacity, travel effort, safety, skill, value, and confidence inputs.
2. Compute explainable dispatch-now versus monitor rankings.
3. Mark simulated scheduling inputs and preserve the current dispatch ranking.
4. Add comparison and constraint tests.

## Phase 4 — Evidence Timeline

1. Normalize divergence, scenario, drone, CV, operator, work-order, and recovery events.
2. Build a readable timeline with source, evidence level, confidence, and status.
3. Add incident replay using existing state and reduced-motion behavior.

## Phase 5 — Resilience and cyber-physical readiness

1. Add explainable generation, equipment, weather, grid, telemetry, and communications categories.
2. Add simulated equipment, telemetry, grid, and suspicious-control scenarios with explicit truth labels.
3. Add integration readiness for SCADA, CMMS, weather, drone, ERP, grid, and security systems.

## Phase 6 — Reports and judge flow

1. Build an evidence package from existing decision state.
2. Add a guided judge sequence using the same dispatch, scenario, evidence, work-order, and recovery state.
3. Add print/export fallback and retry behavior.

## Phase 7 — Verification

1. Run type-check, unit/component tests, lint, production build, accessibility checks, and Impeccable detector.
2. Verify desktop/mobile, keyboard, reduced motion, missing services, missing telemetry, and conflicting evidence.
3. Perform one bounded browser QA and truth-language pass.

## Delivery order

Evidence/recovery foundation → Recovery Tracker → optimizer → timeline → resilience → reports/judge flow → verification.

Every phase remains usable without WebGL, CV, security telemetry, or production integrations.
