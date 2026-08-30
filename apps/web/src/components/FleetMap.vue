<script setup lang="ts">
/**
 * Fleet map — Screen 1, left column.
 *
 * At 13 sites the map's job is CONTEXT ("this is a distributed fleet"), not
 * navigation. The ranked list does navigation. Keep it that way.
 *
 * The hard problem this component exists to solve: five of the Agassi sites
 * carry BYTE-IDENTICAL coordinates (36.1952, -115.1582) because PVDAQ records
 * one coordinate for the whole school campus. Plain markers stack perfectly —
 * you would see one pin and be able to click only the topmost.
 *
 * The fix is markercluster's spiderfy: coincident markers collapse to a badge
 * showing the count, and fan onto radial legs on click. That is honest — the
 * badge says "5 sites here", which is true, and the fan reads as a UI
 * affordance rather than a claim about geography.
 *
 * DO NOT jitter coordinates to fake separation. It invents positions the
 * dataset does not contain. Same principle as the rule against rendering a
 * panel grid.
 */
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import { defineAsyncComponent } from 'vue'
import { TriangleAlert, Diamond, CircleCheck, Box } from '@lucide/vue'
import type { Site, SiteStatus } from '@/types/dispatch'

/**
 * Lazy on purpose. deck.gl alone is roughly 1 MB before gzip — bundling it
 * into the eagerly-loaded main chunk means every visitor pays for it on the
 * landing screen, whether or not they ever open the 3D tab. This keeps it in
 * its own chunk, fetched only the first time someone clicks "3D".
 */
const FleetSkyline3D = defineAsyncComponent({
  loader: () => import('@/components/FleetSkyline3D.vue'),
  delay: 0,
  // A cold chunk fetch is the one moment this tab is legitimately blank; name
  // it so that reads as "loading" rather than "broken".
  loadingComponent: {
    template: '<p class="map-3d-loading">Loading 3D view…</p>',
  },
})

const props = defineProps<{
  sites: Site[]
  /** Site currently highlighted from the list, if any. */
  activeSiteId?: string | null
}>()

const emit = defineEmits<{
  (event: 'select', siteId: string): void
  /** Lets the parent screen give the 3D skyline more room — it is the one
   *  view here where the extra dimension is wasted in a narrow sidebar. */
  (event: 'view-change', view: MapViewMode): void
}>()

const container = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let clusterGroup: L.MarkerClusterGroup | null = null
let baseLayer: L.TileLayer | null = null
const markersBySiteId = new Map<string, L.Marker>()

/**
 * Esri's gray canvas, light and dark, on purpose and after checking alternatives.
 *
 * CARTO's free raster tiles now burn "API KEY REQUIRED" across every tile —
 * they return 200, so nothing errors and nothing logs, the watermark just sits
 * over the fleet map. OpenStreetMap's own servers return a 418 "access blocked"
 * tile to anything their usage policy does not recognise, which is not a
 * dependency to carry into a public judging window.
 *
 * Both endpoints below need no key, and being desaturated they let the status
 * markers carry the only color on the map, which is the point of the screen.
 */
const ESRI_ROOT = 'https://server.arcgisonline.com/ArcGIS/rest/services'
const BASEMAP = {
  light: `${ESRI_ROOT}/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`,
  dark: `${ESRI_ROOT}/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`,
  /**
   * AERIAL IS THE ONE HONEST WAY TO "SHOW THE PRODUCT".
   *
   * PVDAQ publishes no panel positions, no array geometry and no site plans —
   * which is why `CLAUDE.md` forbids rendering a panel grid, and why a 3D model
   * of a site would be invented geometry in a product whose whole claim is that
   * it needs no site-grade instrumentation.
   *
   * Satellite imagery is the opposite: it is a real photograph of the real
   * roof at coordinates the dataset actually contains. Zoom into the Agassi
   * Academy and the arrays are there, in the world, unretouched. Nothing is
   * modelled and nothing is claimed.
   */
  aerial: `${ESRI_ROOT}/World_Imagery/MapServer/tile/{z}/{y}/{x}`,
} as const

type MapViewMode = 'map' | 'aerial' | '3d'
const view = ref<MapViewMode>('map')

/**
 * Resolve the theme the same way theme.css does, and in the same order: an
 * explicit `data-theme` stamp wins, and only when there is none does the OS
 * preference decide. Reading just one of the two gets it wrong in the state
 * most viewers are actually in — unstamped, following their system.
 */
function prefersDark(): boolean {
  const stamped = document.documentElement.dataset.theme
  if (stamped === 'dark') return true
  if (stamped === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** Aerial imagery is photographic and ignores the theme; the canvas follows it. */
function basemapUrl(): string {
  if (view.value === 'aerial') return BASEMAP.aerial
  return prefersDark() ? BASEMAP.dark : BASEMAP.light
}

/**
 * Covers all three view keys so it indexes on `MapViewMode` without a type
 * guard at every call site. The '3d' entry is never actually shown here — the
 * Leaflet tile layer is hidden (not attributed) while that view is active, and
 * FleetSkyline3D's own Esri Imagery / world-atlas attribution takes over. It
 * exists so ATTRIBUTION is a total function of the view, which is one honest
 * fact instead of three places independently trusting the initial 'map'.
 */
const ATTRIBUTION = {
  map: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
  aerial:
    'Imagery &copy; Esri &mdash; Esri, Maxar, Earthstar Geographics, and the GIS User Community',
  '3d': '',
} as const

/** '3d' has no Leaflet tile layer — the skyline is a separate WebGL canvas
 *  handed its own attribution inside FleetSkyline3D. */
function applyBasemap(): void {
  if (!baseLayer || view.value === '3d') return
  baseLayer.setUrl(basemapUrl())
  // Attribution is a licence condition, not decoration — it has to change with
  // the layer it credits.
  baseLayer.options.attribution = ATTRIBUTION[view.value]
  map?.attributionControl.remove()
  map?.attributionControl.addTo(map)
}

function setView(next: MapViewMode): void {
  if (view.value === next) return
  view.value = next
  applyBasemap()
  emit('view-change', next)
  // Leaflet's tile canvas is sized once on mount; toggling away to the 3D
  // panel and back changes this container's box without Leaflet knowing, so
  // its internal size cache goes stale and tiles render into the wrong
  // bounds until interacted with.
  if (next !== '3d') requestAnimationFrame(() => map?.invalidateSize())
}

/**
 * Status colors are reserved and always pair with a glyph, so meaning never
 * rests on color alone — the same rule the list rows follow. Same icon
 * vocabulary as DispatchView and InverterPanel: triangle = needs action,
 * diamond = watch it, circle-check = fine.
 *
 * Leaflet renders marker icons and popups from raw HTML strings OUTSIDE
 * Vue's tree, so a Vue icon component cannot be mounted here — these are the
 * exact stroke paths lucide's TriangleAlert / Diamond / CircleCheck ship,
 * reproduced as literal SVG markup so the marker matches the rest of the
 * product's icon language pixel-for-pixel rather than approximating it.
 */
const STATUS_ICON_PATH: Record<SiteStatus, string> = {
  dispatch:
    '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>' +
    '<path d="M12 9v4"/><path d="M12 17h.01"/>',
  monitor:
    '<path d="M2.7 10.3a2.41 2.41 0 0 0 0 3.41l7.59 7.59a2.41 2.41 0 0 0 3.41 0l7.59-7.59a2.41 ' +
    '2.41 0 0 0 0-3.41l-7.59-7.59a2.41 2.41 0 0 0-3.41 0Z"/>',
  healthy: '<circle cx="12" cy="12" r="10"/><path d="m16 9-5.5 5.5L8 12"/>',
}

const STATUS_STYLE: Record<SiteStatus, { color: string }> = {
  dispatch: { color: 'var(--status-critical)' },
  monitor: { color: 'var(--status-warning)' },
  healthy: { color: 'var(--status-good)' },
}

function markerSvg(status: SiteStatus): string {
  return (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round" width="15" height="15">' +
    STATUS_ICON_PATH[status] +
    '</svg>'
  )
}

function buildIcon(site: Site, isActive: boolean): L.DivIcon {
  const style = STATUS_STYLE[site.status]
  return L.divIcon({
    className: 'fleet-marker-wrapper',
    html: `<span class="fleet-marker${isActive ? ' fleet-marker--active' : ''}"
                 style="color:${style.color}"
                 title="${site.name} — ${site.status}">${markerSvg(site.status)}</span>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  })
}

function popupHtml(site: Site): string {
  const money = site.economics
    ? `<div class="fleet-popup__money">RM ${Math.round(
        site.economics.rm_at_risk_monthly,
      ).toLocaleString('en-MY')}/mo at risk</div>`
    : ''
  return `
    <div class="fleet-popup">
      <div class="fleet-popup__name">${site.name}</div>
      <div class="fleet-popup__meta">${Math.round(site.capacity_kwp)} kWp · ${site.address}</div>
      <div class="fleet-popup__status fleet-popup__status--${site.status}">${site.status}</div>
      ${money}
    </div>`
}

function renderMarkers(): void {
  if (!map || !clusterGroup) return

  clusterGroup.clearLayers()
  markersBySiteId.clear()

  for (const site of props.sites) {
    const marker = L.marker([site.lat, site.lon], {
      icon: buildIcon(site, site.site_id === props.activeSiteId),
      title: site.name,
    })
    marker.bindPopup(popupHtml(site))
    marker.on('click', () => emit('select', site.site_id))
    markersBySiteId.set(site.site_id, marker)
    clusterGroup.addLayer(marker)
  }

  const bounds = clusterGroup.getBounds()
  if (bounds.isValid()) {
    // padded so edge markers are not flush against the frame
    map.fitBounds(bounds, { padding: [32, 32], maxZoom: 9 })
  }
}

let themeObserver: MutationObserver | null = null
let darkQuery: MediaQueryList | null = null

onMounted(() => {
  if (!container.value) return

  map = L.map(container.value, {
    scrollWheelZoom: false, // page scroll should not zoom the map out from under you
    attributionControl: true,
  })

  baseLayer = L.tileLayer(basemapUrl(), {
    attribution: ATTRIBUTION[view.value],
    maxZoom: 19,
  }).addTo(map)

  clusterGroup = L.markerClusterGroup({
    showCoverageOnHover: false,
    // Coincident markers must always fan out — this is the whole point.
    spiderfyOnMaxZoom: true,
    zoomToBoundsOnClick: true,
    maxClusterRadius: 40,
  })
  map.addLayer(clusterGroup)

  renderMarkers()

  // Two sources, because the theme has three states. The attribute fires when
  // something stamps an explicit choice; the media query fires for everyone
  // else, which today is every viewer — nothing in the app sets data-theme yet.
  themeObserver = new MutationObserver(applyBasemap)
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  })
  darkQuery = window.matchMedia('(prefers-color-scheme: dark)')
  darkQuery.addEventListener('change', applyBasemap)
})

onBeforeUnmount(() => {
  themeObserver?.disconnect()
  themeObserver = null
  darkQuery?.removeEventListener('change', applyBasemap)
  darkQuery = null
  map?.remove()
  map = null
  clusterGroup = null
  baseLayer = null
  markersBySiteId.clear()
})

watch(() => props.sites, renderMarkers, { deep: false })

watch(
  () => props.activeSiteId,
  (siteId) => {
    for (const [id, marker] of markersBySiteId) {
      const site = props.sites.find((item) => item.site_id === id)
      if (site) marker.setIcon(buildIcon(site, id === siteId))
    }
    if (!siteId || !clusterGroup) return
    const marker = markersBySiteId.get(siteId)
    if (marker) {
      // Fans the cluster open if the target is hidden inside one.
      clusterGroup.zoomToShowLayer(marker, () => marker.openPopup())
    }
  },
)
</script>

<template>
  <div class="map-frame">
    <div class="map-shell" :data-view="view">
      <div v-show="view !== '3d'" ref="container" class="map-canvas"></div>
      <FleetSkyline3D
        v-if="view === '3d'"
        :sites="sites"
        :active-site-id="activeSiteId"
        @select="(id) => emit('select', id)"
      />

      <!--
        Three named views rather than unlabelled icons: a first-time viewer
        cannot guess what "3D" gives them without the word, let alone an icon.
      -->
      <div class="map-views" role="group" aria-label="Basemap">
        <button
          type="button"
          class="map-views__button"
          :class="{ 'map-views__button--active': view === 'map' }"
          :aria-pressed="view === 'map'"
          @click="setView('map')"
        >
          Map
        </button>
        <button
          type="button"
          class="map-views__button"
          :class="{ 'map-views__button--active': view === 'aerial' }"
          :aria-pressed="view === 'aerial'"
          @click="setView('aerial')"
        >
          Aerial
        </button>
        <button
          type="button"
          class="map-views__button map-views__button--3d"
          :class="{ 'map-views__button--active': view === '3d' }"
          :aria-pressed="view === '3d'"
          @click="setView('3d')"
        >
          <Box :size="12" aria-hidden="true" /> 3D
        </button>
      </div>
    </div>
    <p v-if="view !== '3d'" class="map-legend">
      <span class="map-legend__item">
        <TriangleAlert class="map-legend__glyph map-legend__glyph--dispatch" :size="13" aria-hidden="true" />
        dispatch
      </span>
      <span class="map-legend__item">
        <Diamond class="map-legend__glyph map-legend__glyph--monitor" :size="13" aria-hidden="true" />
        monitor
      </span>
      <span class="map-legend__item">
        <CircleCheck class="map-legend__glyph map-legend__glyph--healthy" :size="13" aria-hidden="true" />
        healthy
      </span>
      <span class="map-legend__hint">
        numbered circles group nearby sites — click to fan out, then zoom in on Aerial to see the
        array itself, or switch to 3D for a risk skyline
      </span>
    </p>
  </div>
</template>

<style scoped>
.map-frame {
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--surface-1);
}

/*
 * Height is set from the FLEET'S OWN ASPECT, not from the viewport.
 *
 * `fitBounds` zooms until the bounding box fits BOTH axes, so the more
 * constrained axis wins. This fleet spans roughly 3,600 km east-west and
 * 500 km north-south — a very wide, flat box — inside a column that is at
 * most 420px wide. Width is therefore always the binding constraint, and at
 * 50vh the leftover vertical space was filled with several thousand km of
 * empty ocean and continent: the screen opened on a map of the Americas
 * rather than a map of the fleet.
 *
 * A shorter frame spends the pixels on the sites instead. It cannot change
 * the zoom — width still decides that — but it stops the map from paying for
 * latitude nobody is looking at.
 */
.map-shell {
  position: relative;
}

.map-canvas {
  height: 320px;
  width: 100%;
}

@media (max-width: 900px) {
  .map-canvas {
    height: 260px;
  }
}

/* Above Leaflet's own panes (400) and controls (800), below the app nav (20
   on a different stacking context) — see the z-index note in theme.css. */
.map-views {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  z-index: 900;
  display: flex;
  overflow: hidden;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.16);
}

.map-views__button {
  padding: 0.3rem 0.6rem;
  background: transparent;
  color: var(--text-secondary);
  border: none;
  font: inherit;
  font-family: var(--font-display);
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background-color var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out);
}

.map-views__button + .map-views__button {
  border-left: 1px solid var(--border-hairline);
}

.map-views__button--3d {
  display: inline-flex;
  align-items: center;
  gap: 0.3em;
}

.map-views__button:hover {
  color: var(--text-primary);
  background: var(--callout-info-bg);
}

/* The selected view is the one place a segmented control needs the accent —
   it is a selection state, which is the role brand colour plays here. */
.map-views__button--active {
  background: var(--action-fill);
  color: var(--action-ink);
}

.map-views__button--active:hover {
  background: var(--action-fill-hover);
  color: var(--action-ink);
}

.map-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: center;
  margin: 0;
  padding: 0.5rem 0.7rem;
  border-top: 1px solid var(--border-hairline);
  font-size: 0.7rem;
  color: var(--text-muted);
}

.map-legend__item {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.map-legend__glyph {
  flex: none;
}

.map-legend__glyph--dispatch {
  color: var(--status-critical);
}
.map-legend__glyph--monitor {
  color: var(--status-warning);
}
.map-legend__glyph--healthy {
  color: var(--status-good);
}

.map-legend__hint {
  flex-basis: 100%;
  color: var(--text-muted);
  opacity: 0.8;
}

.map-3d-loading {
  display: grid;
  place-items: center;
  height: 480px;
  margin: 0;
  color: var(--text-muted);
  font-size: 0.85rem;
}

@media (max-width: 900px) {
  .map-3d-loading {
    height: 360px;
  }
}
</style>

<!--
  Leaflet renders markers and popups outside this component's scoped styles,
  so these must be global.
-->
<style>
.fleet-marker {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  line-height: 1;
  cursor: pointer;
  transition: transform var(--duration-fast, 140ms) ease;
}

.fleet-marker svg {
  /* A surface-colored ring keeps overlapping marks legible, same intent as
     the old text-shadow trick, expressed for a stroked SVG instead of text. */
  filter:
    drop-shadow(0 0 2px var(--surface-1, #fff))
    drop-shadow(0 0 2px var(--surface-1, #fff));
}

/*
 * Aerial imagery is photographic and mostly dark, so the ring cannot follow
 * the theme here: in dark mode --surface-1 is near-black and the halo would
 * vanish into the satellite photo exactly where the marker needs separating
 * from it. Pinned white, and strengthened, because a rooftop is a far busier
 * backdrop than a flat canvas.
 */
.map-shell[data-view='aerial'] .fleet-marker svg {
  filter:
    drop-shadow(0 0 2px rgba(255, 255, 255, 0.95))
    drop-shadow(0 0 3px rgba(255, 255, 255, 0.85))
    drop-shadow(0 1px 2px rgba(0, 0, 0, 0.5));
}

.fleet-marker--active {
  transform: scale(1.5);
}

.fleet-popup__name {
  font-weight: 700;
  font-size: 0.85rem;
  margin-bottom: 0.15rem;
}

.fleet-popup__meta {
  font-size: 0.72rem;
  color: #52514e;
  margin-bottom: 0.3rem;
}

.fleet-popup__status {
  display: inline-block;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.1em 0.4em;
  border-radius: 3px;
  border: 1px solid currentColor;
}

.fleet-popup__status--dispatch {
  color: #d03b3b;
}
.fleet-popup__status--monitor {
  color: #b07d00;
}
.fleet-popup__status--healthy {
  color: #0ca30c;
}

.fleet-popup__money {
  margin-top: 0.3rem;
  font-weight: 700;
  font-size: 0.8rem;
}

/* Leaflet's default cluster bubbles are a green/yellow/orange scale that
   collides with our reserved status colors. Neutralise them — a cluster
   count is not a triage state. */
.marker-cluster-small,
.marker-cluster-medium,
.marker-cluster-large {
  background-color: rgba(137, 135, 129, 0.3);
}

.marker-cluster-small div,
.marker-cluster-medium div,
.marker-cluster-large div {
  background-color: rgba(82, 81, 78, 0.85);
  color: #fff;
  font-weight: 700;
}
</style>
