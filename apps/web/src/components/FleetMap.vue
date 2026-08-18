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
import type { Site, SiteStatus } from '@/types/dispatch'

const props = defineProps<{
  sites: Site[]
  /** Site currently highlighted from the list, if any. */
  activeSiteId?: string | null
}>()

const emit = defineEmits<{
  (event: 'select', siteId: string): void
}>()

const container = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let clusterGroup: L.MarkerClusterGroup | null = null
const markersBySiteId = new Map<string, L.Marker>()

/**
 * Status colors are reserved and always pair with a glyph, so meaning never
 * rests on color alone — the same rule the list rows follow.
 */
const STATUS_STYLE: Record<SiteStatus, { color: string; glyph: string }> = {
  dispatch: { color: 'var(--status-critical)', glyph: '▲' },
  monitor: { color: 'var(--status-warning)', glyph: '◆' },
  healthy: { color: 'var(--status-good)', glyph: '●' },
}

function buildIcon(site: Site, isActive: boolean): L.DivIcon {
  const style = STATUS_STYLE[site.status]
  return L.divIcon({
    className: 'fleet-marker-wrapper',
    html: `<span class="fleet-marker${isActive ? ' fleet-marker--active' : ''}"
                 style="color:${style.color}"
                 title="${site.name} — ${site.status}">${style.glyph}</span>`,
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

onMounted(() => {
  if (!container.value) return

  map = L.map(container.value, {
    scrollWheelZoom: false, // page scroll should not zoom the map out from under you
    attributionControl: true,
  })

  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
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
})

onBeforeUnmount(() => {
  map?.remove()
  map = null
  clusterGroup = null
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
    <div ref="container" class="map-canvas"></div>
    <p class="map-legend">
      <span class="map-legend__item"><span class="map-legend__glyph map-legend__glyph--dispatch">▲</span> dispatch</span>
      <span class="map-legend__item"><span class="map-legend__glyph map-legend__glyph--monitor">◆</span> monitor</span>
      <span class="map-legend__item"><span class="map-legend__glyph map-legend__glyph--healthy">●</span> healthy</span>
      <span class="map-legend__hint">numbered circles group nearby sites — click to fan out</span>
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

/* Half the viewport height. Tall enough that the Vegas and Mid-Atlantic
   clusters are both readable without zooming, and it stays put while the
   list scrolls beside it. */
.map-canvas {
  height: 50vh;
  min-height: 380px;
  width: 100%;
}

@media (max-width: 900px) {
  .map-canvas {
    height: 42vh;
    min-height: 260px;
  }
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
  font-size: 14px;
  line-height: 1;
  /* A surface-colored ring keeps overlapping marks legible. */
  text-shadow:
    0 0 3px var(--surface-1),
    0 0 3px var(--surface-1),
    0 0 3px var(--surface-1);
  cursor: pointer;
  transition: transform 120ms ease;
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
