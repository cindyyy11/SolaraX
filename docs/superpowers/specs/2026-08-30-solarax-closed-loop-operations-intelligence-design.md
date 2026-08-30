# SolaraX Closed-Loop Operations Intelligence

## Status

Approved product direction. This specification extends the existing dispatch, Spatial Operations, CV evidence, work-order, and fleet-health workflow without introducing unsupported production claims.

## Objective

Differentiate SolaraX as a closed-loop solar operations intelligence system:

`Detect loss → Simulate cause → Inspect → Assess resilience → Dispatch → Verify recovery`

The operator workflow leads. Judge-facing presentation uses the same state, calculations, and evidence rather than a separate fabricated experience.

## Product architecture

The system has five connected surfaces:

- Dispatch: ranked operational decisions and avoided visits.
- Spatial Operations: scenario comparison, site simulation, drone inspection, and CV evidence.
- Recovery: completed interventions, post-work telemetry, recovered generation, and payback.
- Resilience: generation, equipment, weather, grid, telemetry, and cyber-physical exposure.
- Reports: evidence packages for operators, management, and judging.

## Recovery Tracker

Recovery records connect a work order to its pre-intervention baseline, projected recovery, post-work observation window, actual recovery, recovered kWh, recovered RM, payback period, and confidence. Until sufficient post-work telemetry exists, the state is `Recovery pending`; missing data is never represented as zero recovery.

Projected and verified recovery remain visually distinct. The tracker explains the baseline period, comparison method, tariff, observation window, and uncertainty. It may show cumulative value only from verified or explicitly projected records.

## Fleet Intervention Optimizer

The optimizer compares dispatch candidates using recoverable revenue, safety urgency, evidence confidence, travel effort, required skill, and available technician capacity. It extends the existing dispatch result without silently replacing it. Operators can compare `Dispatch now` with `Monitor` and inspect every ranking input.

The initial implementation may use bounded illustrative travel and capacity inputs when operational scheduling data is unavailable. Those values must be labelled simulated and remain editable.

## Unified Evidence Timeline

A typed evidence-event model connects:

- Performance divergence
- Scenario application
- Drone route and waypoint
- CV result
- Operator evidence decision
- Work-order creation and completion
- Recovery verification

Events carry timestamp, source, evidence level, confidence, status, and an immutable reference to their source record. Simulated events cannot mutate measured dispatch history.

## Resilience and cyber-physical awareness

The Resilience surface summarizes exposure across generation, equipment, weather, grid, telemetry, and communications. It explains each contributing signal rather than presenting an opaque score.

Cyber-physical classification separates likely equipment anomalies, sensor or telemetry faults, grid-side events, and suspicious control or data patterns. Without live security telemetry, these are simulated scenarios and readiness indicators—not real attack detection.

Incident Replay presents the evidence sequence using measured and simulated labels. Scenario comparison lets operators compare two interventions by projected cost, recovery, confidence, safety, and operational effort.

## Integration readiness

An integration-readiness panel describes available and missing connections for SCADA, CMMS, weather, drone, ERP, grid, and security systems. It reports configuration state and expected data contracts without claiming a live integration.

Reports export a readable evidence package containing the decision, calculations, assumptions, source status, inspection evidence, work order, and recovery status.

## Operator workflow

1. Review measured divergence and economic exposure.
2. Compare monitored and dispatched outcomes.
3. Apply a bounded scenario.
4. Inspect the affected layer and scenario-specific drone route.
5. Review CV or field evidence.
6. Assess relevant resilience indicators.
7. Confirm the operational decision and generate a work order.
8. Verify recovery when post-work telemetry becomes sufficient.

## Data boundaries

- Recovery remains projected until post-maintenance telemetry supports verification.
- CV remains corroborating evidence and cannot silently change ranking or economics.
- Drone routes remain inspection plans, not autonomous-flight claims.
- Digital-twin geometry remains illustrative until verified site geometry is supplied.
- Cybersecurity surfaces show simulated risks or connected evidence; they do not claim attack detection without source telemetry.
- Judge Mode cannot introduce separate business values or unsupported customer claims.

## Failure and empty states

- Missing post-work telemetry: show `Recovery pending`, the missing observation period, and the next eligible date.
- Missing CV: preserve the electrical-evidence workflow.
- Conflicting evidence: show both signals and route to human verification.
- Missing grid or security integrations: expose readiness and simulated scenarios.
- Missing capacity inputs: use an editable simulated assumption and exclude it from measured claims.
- Export failure: preserve the evidence package in the UI and offer retry.

## Accessibility and performance

- Every score, timeline event, optimizer decision, and visual state has a readable text equivalent.
- Keyboard and touch order follow the operator workflow.
- Reduced motion preserves incident state without animated replay.
- Heavy visualization remains lazy-loaded and pauses when hidden.
- Reports and evidence remain usable without WebGL or CV service access.

## Acceptance criteria

1. A completed work order can enter pending, projected, and verified recovery states without changing source dispatch data.
2. Recovery arithmetic exposes baseline, tariff, window, confidence, and status.
3. Optimizer rankings expose every input and distinguish measured from simulated factors.
4. Evidence timeline events retain source, timestamp, evidence level, confidence, and immutable references.
5. Resilience categories explain their contributing signals and missing integrations.
6. Cyber-physical scenarios cannot be mistaken for live attack detection.
7. The operator can move from dispatch through evidence and work order to recovery without a disconnected workflow.
8. Judge Mode uses the same data and state as Operator Mode.
9. Missing-data, conflict, unavailable-service, and export-retry paths remain actionable.
10. Type-check, calculation tests, component tests, lint, production build, accessibility review, and bounded browser QA pass.

## Industry alignment

This direction follows current industry emphasis on interoperable PV digital twins, AI/IoT-supported O&M, situational awareness, grid reliability, and DER cybersecurity. Authoritative references include the 2026 IEA-PVPS report on digitalisation and digital twins and the US Department of Energy guidance on systems integration and solar cybersecurity.
