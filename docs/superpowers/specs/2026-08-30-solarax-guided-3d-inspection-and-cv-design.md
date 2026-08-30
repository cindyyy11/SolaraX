# SolaraX Guided 3D Inspection and CV Verification

## Status

Approved design. This specification extends the Scenario Studio and Spatial Operations design without changing the measured dispatch artifact.

## Objective

Turn Spatial Operations into a credible guided inspection cockpit: scenario-specific 3D behavior, purposeful drone routes, optional exploration, and a computer-vision workflow that answers whether uploaded evidence supports the current dispatch recommendation.

## Spatial simulation

The polished lightweight scene is the default Operational view. A synchronized Interactive 3D view uses the lazy-loaded Three.js renderer for orbit and exploration. Both views expose the same scenario, route, waypoint, severity, summary, and evidence state. Switching views preserves the current inspection context. Operational view remains available when WebGL is loading, unsupported, or lost.

The simulation toolbar contains a clear `Operational | Interactive 3D` switch. Overview, Array, Anomaly, and Drone Route camera controls operate within the selected renderer and may never target a hidden scene. Operational view leads daily use; Interactive 3D is an optional exploration layer.

The scene supports illustrative warehouse roof, commercial complex, and ground-mounted array configurations. Site selection may choose a configuration for demonstration variety, but the interface must state that building, equipment, route, and defect geometry are simulated.

Scenario severity changes the visible affected area and intensity as well as the bounded calculation. The active scenario receives a prominent scene label and a concise explanation of what changed. Scenario selection changes camera framing, environment, equipment state, route geometry, and drone behavior:

- Soiling: full-array serpentine survey with distributed dust coverage.
- Partial shading: perimeter and obstruction pass with a visible shadow path.
- Inverter derating: direct equipment inspection with reduced energy flow.
- String underperformance: row-following electrical trace with one weakened string.
- Thermal hotspot: close thermal orbit around a simulated suspect module.
- Storm damage: safety perimeter followed by a bounded damage sweep.
- Heatwave: high-altitude thermal overview with heat-stress treatment.
- Curtailment: inverter-to-grid connection trace with capped energy flow.

Each guided route contains typed waypoints. Selecting a waypoint pauses the drone, frames the relevant region, and explains what the operator should verify. The route timeline provides previous, next, play, pause, and reset controls. Route geometry must be visibly different between scenarios rather than reusing a generic loop.

Explore mode adds orbit controls and optional manual drone positioning. It is secondary to Guided Inspection mode, visibly labelled illustrative, and cannot change scenario calculations or evidence state.

## Computer-vision verification

The CV workspace leads with: “Does this image support the current dispatch recommendation?”

The flow is:

1. Upload through drag-and-drop, file selection, or supported mobile camera capture.
2. Preview and validate format, size, resolution, and usability before analysis.
3. Show progress through validating, uploading, analysing, and preparing evidence.
4. Review the original and analysed image through toggle and split-view modes.
5. Select a finding to synchronize the image region, finding detail, confidence, and relevant inspection point.
6. Record one operator decision: supports dispatch, needs field verification, or does not support dispatch.
7. Optionally send a typed focus request to Spatial Operations.

Confidence uses a numeric value, plain-language strength, and review guidance. Model version, evidence type, timestamp, and inference mode remain available without dominating the review surface.

CV evidence never automatically changes site status, fleet ranking, economics, or work-order recommendation. When spatial coordinates are absent, 3D handoff uses an explicitly illustrative placement. Empty, rejected, unavailable, low-confidence, and conflicting-evidence states each provide a recovery action.

## State and component boundaries

`SpatialOperations` owns selected scenario state, severity, route, active waypoint, guided/explore mode, and evidence focus. Scenario definitions provide typed visual configuration and route waypoints. The renderer receives these projections and emits interaction intent; it does not calculate business values.

The WebGL scene, CSS fallback, route controls, CV intake, CV review, and operator decision are isolated components with typed interfaces. CV sends a focus request rather than mutating scene or dispatch state directly.

## Accessibility, performance, and failure behavior

- The WebGL bundle and model assets load only when Spatial Operations enters the viewport.
- Rendering pauses when hidden and uses adaptive pixel ratio and reduced geometry on constrained devices.
- No perpetual animation runs outside an active guided inspection.
- Keyboard controls cover route navigation, waypoint selection, camera presets, mode changes, and evidence decisions.
- Reduced motion removes camera travel and drone animation while preserving the selected waypoint and explanation.
- A readable scenario and route summary remains available when WebGL fails.
- Loading and WebGL errors retain scenario controls and provide a retry or lightweight-view action.
- Mobile order is scenario controls, scene, route context, impact, CV evidence, operator decision.

## Verification and acceptance criteria

1. Every supported scenario selects a distinct route, camera framing, and visible scene state.
2. Severity visibly changes affected area or intensity without changing measured site data.
3. Guided routes expose selectable waypoints with operational explanations.
4. Explore mode is optional, interruptible, and cannot change evidence or calculations.
5. WebGL loading or failure preserves the default Operational simulation and readable outputs.
5a. Overview, Array, Anomaly, and Drone Route controls update the renderer currently visible to the user.
5b. Operational and Interactive 3D views preserve the same scenario and waypoint when switching.
6. CV review keeps the original image visible and makes its operational question clear.
7. Findings, confidence, image regions, and spatial focus remain synchronized where source coordinates permit it.
8. Operator evidence decisions remain explicit and do not silently modify dispatch state.
9. Desktop, mobile, keyboard, reduced-motion, and constrained-device paths remain usable.
10. Type-check, tests, lint, production build, accessibility review, and bounded visual QA pass.
11. No physical layout, defect coordinate, autonomous-flight, or production-deployment claim is fabricated.
