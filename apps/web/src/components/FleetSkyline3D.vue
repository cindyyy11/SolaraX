<script setup lang="ts">
/**
 * The fleet as a 3D risk skyline — an orbit-controlled view over the real
 * fleet, where every column's height is a measured number and nothing else.
 *
 * WHAT THIS IS NOT, AND WHY THAT MATTERS. PVDAQ publishes no panel positions,
 * no array geometry and no site plans, and CLAUDE.md forbids rendering a panel
 * grid for exactly that reason: a physical layout the dataset does not
 * contain is a fabrication, however good it looks. This is not that. Nothing
 * here is a model of a roof, a panel or an inverter. It is a bar chart with a
 * third axis, standing on real coordinates, where height is
 * `economics.rm_at_risk_monthly` — a field already on screen elsewhere in the
 * product, read from `dispatch.json`, never invented for the view.
 *
 * WHY A THIRD AXIS EARNS ITS PLACE HERE SPECIFICALLY. The product's whole
 * argument is "most of the fleet is fine, a few sites are bleeding money."
 * Eleven bars mostly at the ground with two sharp spikes standing over them
 * says that in one glance, in a way eleven rows in a list cannot — this is the
 * one screen in the product where the extra dimension carries information a
 * flat view genuinely loses, rather than decorating a view that already had
 * everything it needed.
 *
 * WHY NO BASEMAP TILES. Deck.gl's MapView projects real longitude/latitude
 * correctly on its own — Web Mercator, the same projection Leaflet uses — with
 * no tile server behind it. This project already lost a basemap mid-flight to
 * a provider change (CARTO's free tiles started watermarking with a 200
 * status, so nothing errored and nothing logged); the fix there was fewer
 * live dependencies, not more. The land outline is a single GeoJSON polygon,
 * ~200 KB, generated once from `world-atlas` (Natural Earth data, public
 * domain, ISC licence) and committed as a static asset — see
 * `src/assets/world-land-110m.json`. It never fetches anything at runtime.
 *
 * CONTROLS. Deck.gl's default MapController: drag to pan, right-drag (or
 * ctrl+drag) to rotate and tilt, scroll to zoom. That is the same scheme
 * Google Maps and Mapbox use for 3D, so it needs no bespoke gesture design —
 * a caption states it because the audience for this product has not
 * necessarily met it before.
 */
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { Deck, MapView, LightingEffect, AmbientLight, DirectionalLight } from '@deck.gl/core'
import { ColumnLayer, GeoJsonLayer, TextLayer } from '@deck.gl/layers'
import type { GeoJSON } from 'geojson'
import type { Site, SiteStatus } from '@/types/dispatch'
import worldLandJson from '@/assets/world-land-110m.json'

// Vite's JSON import infers a narrow structural type from the file's actual
// shape; GeoJsonLayer wants the `geojson` package's own type. The runtime
// value is unchanged — this is the same FeatureCollection either way.
const worldLand = worldLandJson as unknown as GeoJSON

const props = defineProps<{
  sites: Site[]
  activeSiteId?: string | null
}>()

const emit = defineEmits<{
  (event: 'select', siteId: string): void
}>()

const container = ref<HTMLDivElement | null>(null)
let deck: Deck<MapView> | null = null
let resizeObserver: ResizeObserver | null = null
let themeObserver: MutationObserver | null = null
let darkQuery: MediaQueryList | null = null

// --- Reference frame ---------------------------------------------------------
// Centred and zoomed on this fleet specifically — not a world view. Picked by
// hand from the fleet's own bounding box (Delaware to Nevada), the same way
// FleetMap's 2D fitBounds derives its window from the real coordinates.
const INITIAL_VIEW_STATE = {
  longitude: -97,
  latitude: 38,
  zoom: 3.35,
  pitch: 50,
  bearing: -12,
  minZoom: 2,
  maxZoom: 10,
  minPitch: 0,
  maxPitch: 75,
}

// --- Status colour, RGBA for deck.gl (0-255 per channel) --------------------
// The identical reserved palette used everywhere else in the product — a
// third dimension is not licence to invent a new colour language.
const STATUS_RGB: Record<SiteStatus, [number, number, number]> = {
  dispatch: [208, 59, 59], // --status-critical
  monitor: [250, 178, 25], // --status-warning
  healthy: [12, 163, 12], // --status-good
}

const MIN_COLUMN_METERS = 900
/** kWh saved -> column metres. Chosen so the two real spikes in this fleet
 *  (RM 1,237 and RM 475) read as spikes without the scale becoming absurd if
 *  a future run has a much larger figure. */
const METERS_PER_RM = 60

/**
 * Coincident-coordinate fan — the 3D analogue of FleetMap's Leaflet spiderfy.
 *
 * Five Agassi sites share one byte-identical (lat, lon), because PVDAQ records
 * one point for the whole campus. Stacked columns at one point would render as
 * a single indistinguishable pillar. The fan is a small, fixed, LABELLED
 * offset around the shared point — not a claim about where the roofs actually
 * are, the same distinction FleetMap's own comment draws for its spiderfy.
 * Never applied to a site with a coordinate it does not share.
 */
const FAN_RADIUS_DEGREES = 0.006

interface SkylineSite extends Site {
  plotLon: number
  plotLat: number
  fanned: boolean
}

function withFannedCoordinates(sites: Site[]): SkylineSite[] {
  const groups = new Map<string, Site[]>()
  for (const site of sites) {
    const key = `${site.lat.toFixed(5)},${site.lon.toFixed(5)}`
    const group = groups.get(key)
    if (group) group.push(site)
    else groups.set(key, [site])
  }

  const result: SkylineSite[] = []
  for (const group of groups.values()) {
    if (group.length === 1) {
      const site = group[0]!
      result.push({ ...site, plotLon: site.lon, plotLat: site.lat, fanned: false })
      continue
    }
    group.forEach((site, index) => {
      const angle = (index / group.length) * Math.PI * 2
      result.push({
        ...site,
        plotLon: site.lon + Math.cos(angle) * FAN_RADIUS_DEGREES,
        plotLat: site.lat + Math.sin(angle) * FAN_RADIUS_DEGREES,
        fanned: true,
      })
    })
  }
  return result
}

function columnHeight(site: Site): number {
  const rm = site.economics?.rm_at_risk_monthly ?? 0
  return Math.max(MIN_COLUMN_METERS, rm * METERS_PER_RM)
}

function prefersDark(): boolean {
  const stamped = document.documentElement.dataset.theme
  if (stamped === 'dark') return true
  if (stamped === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function landColor(): [number, number, number, number] {
  return prefersDark() ? [40, 42, 46, 255] : [225, 224, 217, 255]
}

/** The canvas has no WebGL clear-colour set — see the note by its creation.
 *  This is the CSS colour the container shows behind the transparent canvas,
 *  read from the same tokens the rest of the page uses for its ground plane. */
function backgroundColor(): string {
  return prefersDark() ? '#0d0d0d' : '#f9f9f7'
}

function buildLayers(sites: SkylineSite[]) {
  const land = new GeoJsonLayer({
    id: 'land',
    data: worldLand,
    stroked: false,
    filled: true,
    getFillColor: landColor(),
  })

  const columns = new ColumnLayer<SkylineSite>({
    id: 'sites',
    data: sites,
    diskResolution: 8,
    // Meters, deck.gl's default radius unit — deliberately not `'pixels'`.
    // Pixel-space sizing is a 2D-marker convention (the Leaflet triangle,
    // diamond and circle glyphs use it for exactly that reason); an EXTRUDED
    // column is real 3D geometry, built from world-space vertices, and asking
    // for it in screen pixels is the less natural fit of the two units deck.gl
    // offers here. This fleet spans Delaware to Nevada, framed at zoom ~3.35
    // where one pixel already covers roughly 15 km, so the radius has to be
    // tens of kilometres to clear a handful of pixels at the fleet overview —
    // a physically real size, not a marker convention, and the columns grow
    // accordingly on zooming into one region, the way a real extruded object
    // on a map should.
    radius: 16000,
    extruded: true,
    getPosition: (site) => [site.plotLon, site.plotLat],
    getElevation: columnHeight,
    getFillColor: (site) => [...STATUS_RGB[site.status], 235],
    pickable: true,
    autoHighlight: true,
    highlightColor: [255, 255, 255, 90],
    transitions: { getElevation: 400 },
  })

  // Labels only for sites carrying a real number — a healthy site's label
  // would just repeat "RM 0", which is not information worth the clutter.
  const flagged = sites.filter((site) => (site.economics?.rm_at_risk_monthly ?? 0) > 0)
  const labels = new TextLayer<SkylineSite>({
    id: 'labels',
    data: flagged,
    getPosition: (site) => [site.plotLon, site.plotLat],
    getText: (site) => `RM ${Math.round(site.economics!.rm_at_risk_monthly).toLocaleString('en-MY')}`,
    getSize: 13,
    getColor: prefersDark() ? [242, 244, 248, 230] : [11, 11, 11, 230],
    getPixelOffset: [0, -18],
    fontFamily: 'var(--font-display), system-ui, sans-serif',
    fontWeight: 600,
    billboard: true,
  })

  return [land, columns, labels]
}

function buildLighting(): LightingEffect {
  // Fixed light, not tied to real time of day — this is a data chart, not a
  // simulation, and a sun position that changed with the viewer's clock would
  // imply a claim ("this is what the site looks like now") the data cannot
  // back. Positioned to rake across the columns so extrusion actually reads.
  const ambient = new AmbientLight({ color: [255, 255, 255], intensity: 1.1 })
  const sun = new DirectionalLight({
    color: [255, 255, 255],
    intensity: 1.4,
    direction: [-2, -3, -1],
  })
  return new LightingEffect({ ambient, sun })
}

function render(): void {
  if (!deck) return
  const sites = withFannedCoordinates(props.sites)
  // TEMP DEBUG
  console.log('[skyline debug]', JSON.stringify(sites.map(s => ({ id: s.site_id, lon: s.plotLon, lat: s.plotLat, elev: columnHeight(s), status: s.status }))))
  deck.setProps({ layers: buildLayers(sites), effects: [buildLighting()] })
  if (container.value) container.value.style.backgroundColor = backgroundColor()
}

function resetView(): void {
  // `setProps({ initialViewState })` alone does not re-seed an already-
  // interacted camera in deck.gl's non-React core API — `initialViewState` is
  // only consulted once, at construction. Recreating with a fresh copy of the
  // starting pose is the same reliable path a resize already takes, reused
  // here rather than trusted as a second, less-tested one.
  const size = measuredSize()
  if (!size) return
  lastViewState = { ...INITIAL_VIEW_STATE }
  deck?.finalize()
  createDeck(size)
}

interface TooltipInfo {
  x: number
  y: number
  site: SkylineSite
}

const tooltip = ref<TooltipInfo | null>(null)

/**
 * Measured and passed to `Deck` explicitly at construction, rather than left
 * to deck.gl's default `width: '100%'` and its own internal ResizeObserver.
 *
 * This panel is mounted by a `v-if` on a tab switch, so on its very first
 * frame the container has just been inserted by Vue in the same tick — the
 * kind of moment an auto-sizing observer is more likely to race than the
 * common case of a canvas that has been sitting in the DOM since page load.
 * Measuring synchronously here and handing Deck a known-good size removes
 * that race outright, on the one code path (construction) every one of these
 * libraries exercises by default.
 */
function measuredSize(): { width: number; height: number } | null {
  if (!container.value) return null
  const rect = container.value.getBoundingClientRect()
  return rect.width > 0 && rect.height > 0 ? { width: rect.width, height: rect.height } : null
}

/** Preserves the current camera pose across a recreate, so a resize does not
 *  silently reset whatever the viewer had already dragged the scene to. */
let lastViewState: typeof INITIAL_VIEW_STATE = { ...INITIAL_VIEW_STATE }

function createDeck(size: { width: number; height: number }): void {
  if (!container.value) return

  deck = new Deck({
    parent: container.value,
    width: size.width,
    height: size.height,
    views: new MapView({ id: 'fleet', repeat: false }),
    initialViewState: { ...lastViewState },
    controller: true,
    layers: [],
    getCursor: ({ isHovering }) => (isHovering ? 'pointer' : 'grab'),
    onViewStateChange: ({ viewState }) => {
      lastViewState = viewState as typeof INITIAL_VIEW_STATE
    },
    onClick: (info) => {
      const site = info.object as SkylineSite | undefined
      if (site) emit('select', site.site_id)
    },
    onHover: (info) => {
      const site = info.object as SkylineSite | undefined
      tooltip.value = site ? { x: info.x, y: info.y, site } : null
    },
    onError: (error) => {
      console.error('[FleetSkyline3D] deck.gl error', error)
    },
  })

  render()
}

/** Debounced: a window drag fires many ResizeObserver entries in a row, and
 *  recreating on every one of them would thrash the WebGL context mid-drag. */
let resizeTimer: ReturnType<typeof setTimeout> | null = null

function recreateAtCurrentSize(): void {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    const size = measuredSize()
    if (!size) return
    deck?.finalize()
    createDeck(size)
  }, 150)
}

onMounted(() => {
  if (!container.value) return
  createDeck(measuredSize() ?? { width: 400, height: 320 })

  resizeObserver = new ResizeObserver(recreateAtCurrentSize)
  resizeObserver.observe(container.value)

  themeObserver = new MutationObserver(render)
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  })
  darkQuery = window.matchMedia('(prefers-color-scheme: dark)')
  darkQuery.addEventListener('change', render)
})

onBeforeUnmount(() => {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeObserver?.disconnect()
  themeObserver?.disconnect()
  darkQuery?.removeEventListener('change', render)
  deck?.finalize()
  deck = null
})

watch(() => props.sites, render, { deep: false })
</script>

<template>
  <div class="skyline">
    <div ref="container" class="skyline__canvas"></div>

    <div
      v-if="tooltip"
      class="skyline__tooltip"
      :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }"
    >
      <p class="skyline__tooltip-name">{{ tooltip.site.name }}</p>
      <p class="skyline__tooltip-meta">
        {{ Math.round(tooltip.site.capacity_kwp) }} kWp · {{ tooltip.site.status }}
        <template v-if="tooltip.site.fanned"> · fanned, shares a coordinate</template>
      </p>
      <p v-if="tooltip.site.economics" class="skyline__tooltip-rm">
        RM {{ Math.round(tooltip.site.economics.rm_at_risk_monthly).toLocaleString('en-MY') }}/mo
        at risk
      </p>
    </div>

    <button type="button" class="skyline__reset" @click="resetView">Reset view</button>

    <p class="skyline__caption">
      Column height is real RM at risk this month — not a rendering of any roof or panel, which
      PVDAQ does not publish. Drag to pan · right-drag to tilt &amp; rotate · scroll to zoom.
    </p>
  </div>
</template>

<style scoped>
.skyline {
  position: relative;
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--page-plane);
}

.skyline__canvas {
  height: 480px;
  width: 100%;
  cursor: grab;
}

@media (max-width: 900px) {
  .skyline__canvas {
    height: 360px;
  }
}

.skyline__canvas:active {
  cursor: grabbing;
}

.skyline__tooltip {
  position: absolute;
  z-index: 10;
  transform: translate(12px, -50%);
  padding: 0.55rem 0.75rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
  font-size: 0.78rem;
  line-height: 1.4;
  pointer-events: none;
  max-width: 220px;
}

.skyline__tooltip-name {
  margin: 0;
  font-weight: 700;
  font-family: var(--font-display);
}

.skyline__tooltip-meta {
  margin: 0.15rem 0 0;
  color: var(--text-muted);
  text-transform: capitalize;
}

.skyline__tooltip-rm {
  margin: 0.3rem 0 0;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--action-text);
}

.skyline__reset {
  position: absolute;
  top: 0.6rem;
  right: 0.6rem;
  z-index: 5;
  padding: 0.35rem 0.7rem;
  background: var(--surface-1);
  color: var(--text-secondary);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
  font: inherit;
  font-family: var(--font-display);
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.16);
  transition:
    color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}

.skyline__reset:hover {
  color: var(--action-text);
  border-color: var(--action-text);
}

.skyline__caption {
  position: absolute;
  left: 0.6rem;
  bottom: 0.5rem;
  right: 0.6rem;
  z-index: 5;
  margin: 0;
  font-size: 0.68rem;
  line-height: 1.4;
  color: var(--text-muted);
  text-shadow:
    0 0 4px var(--page-plane),
    0 0 4px var(--page-plane),
    0 0 4px var(--page-plane);
}
</style>
