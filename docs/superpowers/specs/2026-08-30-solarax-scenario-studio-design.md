# SolaraX Scenario Studio and Spatial Operations Redesign

## Status

Approved direction. This specification extends the existing mission-control redesign. It does not authorize fabricated physical site evidence or unsupported production claims.

## Objective

Make SolaraX feel like a distinctive, industry-ready solar operations instrument while making its 3D simulation more useful and more accurate about what is known, inferred, and imagined.

The experience must help an operator answer:

1. What is happening in the fleet?
2. What could explain the divergence?
3. What would the scenario cost and what should happen next?

## Product truth model

Every value or visual element carries one of three evidence levels:

- **Measured** — directly present in the dispatch artifact or source telemetry.
- **Inferred** — calculated from measured values using a documented method.
- **Simulated** — an illustrative scenario or physical placement that is not observed at the site.

Measured and inferred values may update the operational recommendation. Simulated geometry may explain a scenario but may not be presented as site evidence.

The current PVDAQ artifact contains no roof dimensions, panel layout, string topology, inverter placement, drone imagery, or verified defect coordinates. The product must display this limitation near the scene, not hide it in documentation.

## Experience modes

### Operator Mode

The default mode remains a calm, warm editorial operations workspace. It prioritizes dispatch count, RM exposure, ranked sites, evidence, and work-order action. 3D fleet risk is available beside the reliable 2D map. Routine navigation and selection remain fast and never wait for cinematic animation.

### Scenario Lab

Scenario Lab is an explicit workspace for exploring bounded incidents. It shows scenario controls, before/after values, confidence, assumptions, evidence level, 3D state changes, and the recommended response. Reset always returns to the measured baseline.

### Presentation Mode

Presentation Mode uses the same state and data as the product, but provides a short guided sequence for judges or onboarding. It may choreograph camera movement, energy paths, drone flight, and evidence reveals. The mode is user-invoked, interruptible, and never the only path to information.

## Scenario library

Scenarios are typed definitions, not arbitrary visual effects. Each definition has:

- `id`, title, group, and description
- trigger and required inputs
- severity range and duration range
- bounded calculation function
- output metrics and units
- evidence level for each output
- confidence and assumptions
- response options
- scene layers to change
- reset behavior

The initial library covers:

- Revenue loss: soiling, partial shading, inverter derating, string underperformance, telemetry failure.
- Inspection and safety: thermal hotspot, connector heating, damaged module, storm damage, simulated drone verification.
- Grid and environment: heatwave, cloud variability, curtailment, tariff change, and battery/grid response.

Scenario outputs must be derived from the existing expected-versus-actual and economic model where possible. If a scenario requires a value the artifact does not provide, the UI must use a bounded illustrative assumption and label it simulated. It must never silently overwrite the real site record.

## 3D scenes

### Fleet scene

The existing geographic 3D skyline remains the fleet-level view. Height encodes monthly RM exposure, color and text encode dispatch status, and selection remains synchronized with the queue and URL state.

### Site scene

The site scene adds selectable illustrative roof planes, panel groups, inverter units, energy paths, status states, and a drone route. Geometry is labelled “Illustrative simulation.” Physical placement is never described as measured.

### Scenario scene

Scenario changes are visible in the scene:

- Soiling and shading reduce panel-group flow.
- Derating or string loss weakens or stops an equipment path.
- Thermal or connector scenarios reveal a simulated heat zone.
- Storm scenarios alter a bounded set of illustrative panels.
- Drone verification routes to the simulated suspect zone.
- Grid and tariff scenarios change the economic layer, not physical geometry.

Each scene has Overview, Array, Equipment, Anomaly, and Drone camera presets where relevant. A static 2D/table alternative is always present.

## Visual direction

The whole system shares one design language with three tonal states:

- Operator surfaces: warm off-white, graphite, precise rules, editorial typography, solar amber actions.
- Scenario surfaces: dark graphite-green technical workspace, layered equipment linework, compact controls.
- Presentation surfaces: deeper spatial contrast, controlled glow, cinematic camera transitions, and restrained motion.

The redesign removes repeated generic metric-card grids, decorative gradients, arbitrary pills, glowing borders, emoji icons, and continuous ambient animation. Layouts use intentional asymmetry and clear reading order. Existing Lucide icons remain the consistent icon family unless a new authored SVG is necessary for equipment geometry.

Typography uses the existing self-hosted font system as a base, with a more distinctive display face selected only if licensing and bundle size remain acceptable. Data values retain tabular numerals. Body text remains at least 16px on mobile.

## Motion thesis

- Focal moment: a user-invoked incident replay connecting divergence to evidence and dispatch.
- Continuity: camera presets, before/after state, and selected-site context persist across mode changes.
- Feedback: controls acknowledge selection, replay, reset, and scenario application.
- Budget: no more than one expensive scene animation at a time; pause when hidden; never block input.

Motion uses transform and opacity first, bounded glow or clip-path only where it clarifies focus, shared duration/easing tokens, and a reduced-motion representation that preserves state and explanation without camera travel or looping drone motion.

## Data flow and boundaries

The page-level scenario store owns the measured baseline, selected scenario, parameters, derived outputs, evidence labels, and reset state. Scene renderers receive typed projections and emit intent. They do not mutate the dispatch artifact or invent business values.

Scenario calculations are pure functions with unit tests for severity bounds, duration bounds, zero-state reset, economic arithmetic, and evidence labels. The work-order flow receives the scenario recommendation as context and clearly marks any simulated verification as pending field confirmation.

## Error, fallback, and empty states

- Missing or invalid site data: explain which input is unavailable and keep the measured workflow usable.
- WebGL unavailable or lost: preserve selection and scenario state, return to 2D, and show a recovery action.
- Scenario input outside bounds: clamp with an inline explanation; never produce negative generation or risk.
- No evidence: show “No visual evidence available” and keep performance evidence visible.
- Healthy site: do not invent an anomaly beacon; show a healthy baseline and explain that no incident is active.
- Stale data: show timestamp and last successful update while preserving browsing.

## Accessibility and performance

- Every camera, scenario, replay, reset, and response control is keyboard reachable with a visible focus state.
- Status is conveyed with text and shape, not color alone.
- Scene has a concise screen-reader summary and a table/list equivalent for scenario outputs.
- Touch targets are at least 44px; mobile uses a single-column scenario flow without horizontal scroll.
- `prefers-reduced-motion` disables camera travel and looping motion while retaining state transitions.
- Heavy fleet WebGL remains lazy-loaded. Site simulation uses lightweight CSS geometry and reserves its layout dimensions.
- Scenario calculations are synchronous and bounded; expensive rendering pauses when offscreen.

## Verification and acceptance criteria

1. A user can identify the highest-risk site from the default Operator Mode first viewport.
2. A user can select one of the three scenario groups and see its evidence level, assumptions, before/after metrics, and response recommendation.
3. Scenario reset restores every measured value and scene state exactly.
4. The site scene visibly distinguishes measured values from inferred and simulated geometry.
5. Presentation Mode can replay the incident, be interrupted, and finish without changing the underlying dispatch record.
6. 2D mode remains fully usable when WebGL fails or is unavailable.
7. Keyboard-only and reduced-motion paths preserve the full decision workflow.
8. The same scenario state is reflected in the scene, readable metrics, and work-order context.
9. Unit tests cover scenario calculations and reset behavior; type-check, lint, production build, and visual QA pass.
10. No unsupported physical geometry, customer, deployment, or autonomous-drone claim is introduced.

