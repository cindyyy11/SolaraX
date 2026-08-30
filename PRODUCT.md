# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The primary user is a solar asset owner or O&M operator managing a distributed commercial and industrial fleet. During monthly operations, they need to identify which sites deserve a maintenance visit, understand why each site was flagged, and issue a defensible work order without inspecting every site manually.

A secondary audience is a technical or commercial evaluator, including hackathon judges, who needs to understand the product mechanism, evidence, scalability, and operational value quickly.

## Product Purpose

SolaraX is a fleet-triage layer for distributed solar. It identifies the small number of sites that require attention this month, estimates the economic value at risk, and recommends where limited maintenance capacity should be dispatched. Success means the operator can move quickly from fleet overview to evidence-backed action while healthy sites are explicitly cleared from unnecessary visits.

## Positioning

SolaraX uses the fleet itself as a control group. Sites in the same weather region benchmark one another, allowing the system to detect divergence without requiring an on-site irradiance sensor at every installation. The peer signal is complemented by an absolute physics baseline so site-specific and fleet-wide drift are not treated as the same problem.

## Operating Context

The core workflow is monthly maintenance triage:

1. Review the ranked fleet dispatch list.
2. Select a site and inspect the performance, cohort, and economic evidence.
3. Review available visual verification evidence when present.
4. Create or review a work order for the technician.
5. Monitor fleet health and return on avoided visits or recovered generation.

The interface is also demonstrated in a time-constrained judging context, but the daily operator workflow leads product decisions.

## Capabilities and Constraints

- The current web application is implemented in Vue and TypeScript.
- The fleet contains 11 public-data demonstration sites in two climate cohorts.
- NREL PVDAQ supplies real US inverter data to prove the method. It is not a Malaysian production fleet and must not be described as one.
- Satellite irradiance and temperature support the sensor-free baseline.
- Dispatch status, cohort divergence, expected and actual generation, estimated monthly ringgit at risk, and work-order evidence are the primary operator information.
- Visual verification is partial, and simulated outputs must remain clearly labelled.
- Published data does not contain roof, panel, inverter, or array geometry. The product must not present fabricated physical digital twins as evidence.
- A 3D view may encode measured fleet variables spatially, including status and ringgit at risk, as long as its meaning is explicit and a 2D alternative remains available.
- The hackathon MVP does not include live customer integrations, autonomous drone operations, or production deployment claims.

## Brand Commitments

The product name is SolaraX. Existing logo assets under `apps/web/public/brand/` remain authoritative. The voice is concise, technically honest, commercially literate, and explicit about evidence limits.

## Evidence on Hand

- Product requirements: `docs/SolaraX_PRD_v2.md`
- Architecture and implementation status: `docs/ARCHITECTURE.md`
- Method results and limitations: `README.md`
- Fleet and dispatch data: `apps/web/public/dispatch.json`
- Static brand assets: `apps/web/public/brand/`
- Existing 2D fleet map: `apps/web/src/components/FleetMap.vue`
- Existing measured-risk 3D skyline: `apps/web/src/components/FleetSkyline3D.vue`
- Thermal and visual evidence components exist, but any simulated content must retain its label.

No real customer testimonials, production-site geometry, live Malaysian fleet data, or verified deployment claims are available and none may be fabricated.

## Product Principles

1. Lead with the next operational decision, not a collection of metrics.
2. Make evidence and uncertainty visible at the point of action.
3. Use spatial and animated presentation only when it clarifies measured fleet state.
4. Keep healthy sites legible so avoided work is part of the value story.
5. Let the method and claims become more credible, not more theatrical, under scrutiny.

## Accessibility & Inclusion

The web experience must support keyboard navigation, visible focus, readable labels, text contrast meeting WCAG AA, touch targets of at least 44 by 44 CSS pixels, reduced-motion preferences, and a non-WebGL path for the core fleet workflow.

