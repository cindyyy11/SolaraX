# Map Basemap Reliability Design

## Goal

Restore a usable basemap in Screen 1's **Map** view. The current Esri Gray Canvas layer renders
provider tiles labelled "Map data not yet available". The fix must preserve the fleet markers,
marker clustering, Map/Aerial/3D switcher, theme behavior, and required attribution.

This supports the **Technical Feasibility** rubric row by ensuring the public dashboard reliably
renders the fleet's geographic context during judging.

## Architecture and data flow

`FleetMap.vue` remains the only owner of Leaflet basemap selection. The Map view will use the
keyless OpenStreetMap Standard endpoint:

`https://tile.openstreetmap.org/{z}/{x}/{y}.png`

The Aerial view will continue to use Esri World Imagery because OpenStreetMap does not provide
satellite imagery. The 3D view remains a separate deck.gl canvas and is outside this change.

Basemap selection will therefore be based on view, not theme:

- Map -> OpenStreetMap Standard
- Aerial -> Esri World Imagery
- 3D -> no Leaflet tile layer

The OpenStreetMap copyright link and contributor wording will be displayed in Leaflet's
attribution control. Esri attribution remains attached only to the Aerial view.

## Error handling

The Leaflet tile layer will listen for tile-loading failures. A Map-view failure will replace the
failed tile layer with a simple local fallback grid so site markers and controls remain usable and
the page never fills with third-party error tiles. The fallback must not claim to contain map data
and must visibly describe itself as a basemap fallback.

Fallback activation will be idempotent so many simultaneous tile errors cannot repeatedly replace
the layer. Switching views will reset the failure state and install the selected view's correct
layer and attribution.

## Scope boundaries

This change will not alter coordinates, fleet data, marker placement, cluster behavior, site
navigation, Aerial imagery, or the 3D skyline. It will not add an API key or a new package.

## Verification

- Add focused unit tests for Map and Aerial URL/attribution selection and fallback behavior where
  the existing test structure permits it.
- Run the frontend type checker and production build.
- Run the frontend unit tests.
- Inspect the final diff to ensure unrelated working-tree changes are preserved.

