# SolaraX Mission Control Redesign

## Status

Approved design direction. This document defines the redesign scope; it does not authorize fabricated product data or physical site geometry.

## Objective

Redesign SolaraX as an operator-first solar fleet mission-control workspace that is immediately clear in daily use and visually memorable in a hackathon demonstration. The first screen must answer three questions in order:

1. How much of the fleet needs attention?
2. Which site should be reviewed first?
3. What evidence supports the recommendation?

The product's signature visual moment is a switch from a conventional 2D fleet map to a 3D economic-risk landscape. The effect earns its place by encoding measured ringgit at risk and status, not by inventing a physical model of each site.

## Approved Direction

The selected layout is **Mission Control Split**.

On desktop, the first viewport combines a spatial fleet canvas occupying approximately 60 percent of the working area with a ranked attention queue occupying approximately 40 percent. A compact summary strip sits above both. Selecting a site synchronizes the map, queue, and evidence preview.

The visual system is a refined solar-operations instrument: deep graphite and warm off-white planes, restrained solar-lime interaction accents, fine borders, strong typographic hierarchy, and status colors reserved for operational meaning. The 3D surface is cinematic; the controls around it remain calm.

### Concept-challenge raises

The approved direction was challenged against several unrelated visual systems to prevent it from settling into a generic dashboard. None replaced the operator-first mission-control world because each weakened either solar-operations identification or product clarity. The following disciplines strengthen the approved direction without importing their costumes:

- **Direct-address discipline, retained from broadcast teletext:** global search and keyboard navigation make every site and primary action directly reachable.
- **State discipline, retained from the one-bit desktop:** selected, disabled, loading, and unavailable states remain unmistakable even without color or animation.
- **Reversibility discipline, retained from an origami sequence:** movement from fleet to site to work order preserves context and always offers a predictable route back.
- **Semantic-type discipline, retained from the alphabet storm:** typography may move or scale only when it continues to communicate real data and remains readable.
- **Velocity discipline, retained from a racing identity:** the dispatch flow receives decisive forward momentum, while decorative streaks and fictional decals are rejected.
- **Planar discipline, retained from precisionist industrial painting:** a single lighting logic, hard hierarchy, and overlapping planes give the interface visual conviction without ornamental glass effects.

## Information Architecture

The persistent navigation is grouped by operator intent:

- **Dispatch**: landing workspace and ranked monthly action queue.
- **Fleet**: fleet health, cohorts, site browsing, and comparison.
- **Work orders**: recommended, open, and completed maintenance work.
- **Performance**: fleet health, recovered value, avoided visits, and method evidence.

Navigation items use a consistent vector icon and a visible text label at desktop widths. The mobile experience uses a compact navigation pattern with no more than five top-level destinations.

The primary workflow is:

`identify site → review evidence → create or review work order`

The selected site and current view mode must persist while moving through this workflow.

## Dispatch Workspace

### Command header

The header contains the product identity, page title, data freshness, theme control, and a single primary action. The operator receives a plain-language fleet summary such as “Two sites need attention” rather than a generic dashboard greeting.

### Summary strip

The first metric is monthly value at risk. Supporting metrics are dispatch count, healthy-site count, and fleet capacity. Values use tabular figures and retain units. The summary strip must remain compact enough that the spatial canvas and ranked queue are visible in the first desktop viewport.

### Spatial canvas

The canvas supports two mutually exclusive modes:

- **2D Map**: the reliable, low-cost scanning and fallback mode.
- **3D Risk**: an orbit-controlled economic-risk landscape.

Both modes consume the same sites, filters, selected-site state, and status legend. Changing modes does not clear the selection.

The 3D view encodes:

- longitude and latitude from the fleet data;
- column height from monthly ringgit at risk;
- column color from dispatch status;
- selection with outline, illumination, and a synchronized queue state;
- optional cohort boundaries or labels when they remain legible.

The 3D view includes Fleet, Risk, Cohort, and Selected-site camera presets plus a reset control. On-canvas guidance explains orbit, zoom, and the height encoding. It must never imply that columns are physical roofs, panels, inverters, or site structures.

### Ranked queue

The queue is ordered by the existing dispatch ranking. Each actionable row shows site name, status, monthly value at risk, the most decision-relevant evidence statement, and an explicit review action. The selected row has stronger structural emphasis, not color alone.

Healthy sites are collapsed into a reassuring summary after actionable and monitored sites. The operator can expand them when needed.

### Evidence drawer

Selecting a site opens a compact evidence preview without leaving the dispatch context. The drawer presents expected versus actual performance, cohort divergence, data quality, available visual evidence, and a clear path to the full site page. Technical details are progressively disclosed.

## Site Detail and Honest 3D Modeling

Site detail includes an interactive **performance model** showing the flow:

`satellite conditions → expected output → actual output → peer divergence → estimated economic loss`

This is an explanatory data model, not a physical digital twin. It can use depth, particles, or animated energy paths when those elements clarify the calculation. It must carry units, definitions, and a reduced-motion representation.

Realistic solar-panel, roof, inverter, or array models are excluded until genuine geometry is available. Visual verification imagery remains the correct place to inspect physical defects. Simulated evidence retains an unmissable label.

## Visual System

### Color

- Neutral planes provide most of the interface.
- Solar lime marks selection, current state, data freshness, and the primary action.
- Red, amber, and green are reserved for critical, monitored, and healthy operational states.
- Status is always reinforced with text or shape.
- Light and dark themes share the same semantic tokens and hierarchy.

### Typography

Instrument Sans is the primary interface family. A technical monospaced family may be added for IDs, timestamps, compact measurements, and diagnostic values. Large financial and generation values use tabular numerals. Body text is at least 16 pixels on small screens, with labels never falling below a readable 12-pixel floor.

### Surfaces and density

The interface uses fine borders, moderate radii, controlled elevation, and little decorative blur. The spatial canvas is the single visual hero. Surrounding cards stay flatter so evidence remains readable. Spacing follows a 4/8-pixel rhythm.

### Icons

Use the existing Lucide family consistently. Structural emoji are excluded. Icon-only controls require accessible names and at least a 44-by-44-pixel hit area.

## Motion and Interaction

Motion explains state and spatial continuity:

- selected-site emphasis moves coherently between map, queue, and evidence drawer;
- queue reordering animates position without obscuring the final rank;
- 3D risk columns rise once when the 3D mode opens or the metric changes;
- drawers and route-level details enter in approximately 180–280 milliseconds;
- hover and press feedback appears within 100 milliseconds;
- exit motion is slightly faster than entry motion.

Continuous floating, pulsing, rotating, or glowing decoration is excluded. Animations use transform and opacity where practical. With `prefers-reduced-motion`, transitions become immediate or use a restrained opacity change, the 3D camera does not auto-move, and meaning remains intact.

## Responsive Behavior

Desktop retains the split map-and-queue layout. Tablet may narrow the queue or present it as a resizable adjacent panel. Mobile uses a clear segmented control between Map and List rather than squeezing both into one viewport. Selecting a marker in mobile Map mode surfaces a bottom sheet with the same essential evidence and action.

Fixed headers, sheets, and navigation reserve content space and respect safe areas. No primary workflow requires hover, right-click, or a precision gesture. Every gesture has a visible control alternative.

## Supporting Features

The approved supporting scope is:

- global search or command menu for sites and primary actions;
- shareable URLs for selected site, map mode, filters, and evidence view;
- saved 3D camera presets;
- side-by-side expected-versus-actual site comparison;
- persistent work-order state and activity timeline;
- a user-invoked guided demo mode that explains the normal operator workflow without creating a separate product surface.

The redesign does not add live integrations, autonomous dispatch, new prediction claims, or fictional customer content.

## Component Boundaries

The implementation should keep components focused and share state through typed interfaces:

- `AppShell`: navigation, theme, global search, and responsive shell.
- `FleetCommandHeader`: page context, freshness, and primary action.
- `FleetSummaryStrip`: decision-critical aggregate metrics.
- `FleetSpatialCanvas`: mode switching and shared spatial state.
- `FleetMap2D`: Leaflet rendering and fallback.
- `FleetRisk3D`: Deck.gl rendering, presets, and WebGL lifecycle.
- `DispatchQueue`: ranked site list and keyboard selection.
- `SiteEvidenceDrawer`: progressive evidence preview.
- `PerformanceModel`: explanatory energy and economic flow.
- `DemoGuide`: user-invoked guided narration layered over the real interface.

Map renderers must not own authoritative business state. They receive sites, selection, filters, and view configuration and emit user intent. A page-level store or composable synchronizes the renderers with the queue and router.

## Data Flow

The existing dispatch payload remains authoritative. The page loads and validates fleet data, derives summary and display collections, and passes typed values into presentation components. Selection events update the shared state and URL. No component generates fallback business figures.

Heavy 3D dependencies load only when the user requests 3D mode. The canvas reserves its dimensions before loading to prevent layout shift. Theme and resize changes update the current renderer without losing the selected site or camera unexpectedly.

## Error and Empty States

- **Loading**: reserve final layout dimensions and use low-motion skeletons.
- **Stale data**: show the last successful update and keep browsing available.
- **Unavailable dispatch payload**: explain the failure, offer retry, and avoid displaying invented placeholders.
- **WebGL unavailable or lost**: preserve selection and filters, return to 2D, and explain the fallback.
- **No actionable sites**: celebrate fleet health calmly and provide access to monitored and healthy sites.
- **No sites or invalid coordinates**: present a clear data-quality state outside the map canvas.
- **No visual evidence**: explain that performance evidence is still available and do not imply a missing inspection result.

## Accessibility

- Meet WCAG AA contrast for text and meaningful controls in both themes.
- Preserve a logical heading order and DOM reading order.
- Provide a skip link and visible focus rings.
- Make the queue fully keyboard navigable without trapping focus in the map.
- Give canvas controls accessible names and visible text alternatives.
- Never rely on color, height, animation, or pointer hover alone.
- Provide table or list access to every data point represented spatially.
- Support browser zoom, reduced motion, touch targets of at least 44 pixels, and readable mobile typography.

## Verification

Implementation is complete only after:

1. Type checking, unit tests, linting, and production build pass.
2. The core workflow works with keyboard only.
3. 2D and 3D modes preserve selection and filters.
4. WebGL failure falls back without losing operator context.
5. Reduced-motion behavior is verified.
6. Light and dark contrast are checked independently.
7. Layout is visually inspected at representative mobile, tablet, and desktop widths.
8. Existing claim labels and real-data limitations remain visible.
9. A bounded visual QA pass is completed, followed by one consolidated correction pass and one final confirmation.

## Acceptance Criteria

- An operator can identify the highest-priority site from the first viewport.
- The financial impact and next action are readable without interacting with the map.
- Selecting a site synchronizes all visible representations.
- Switching to 3D produces an impressive but truthful view whose encodings are explained on screen.
- The full identify-to-evidence-to-work-order path is predictable across screen sizes.
- The experience remains usable without WebGL, pointer hover, or motion.
- No unsupported physical model, metric, customer, or deployment claim is introduced.
