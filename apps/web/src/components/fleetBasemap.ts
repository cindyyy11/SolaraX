export type MapViewMode = 'map' | 'aerial' | '3d'

export interface BasemapConfig {
  url: string
  attribution: string
  maxZoom: number
}

const OPENSTREETMAP_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

const ESRI_IMAGERY_ATTRIBUTION =
  'Imagery &copy; Esri &mdash; Esri, Maxar, Earthstar Geographics, and the GIS User Community'

const BASEMAPS: Record<'map' | 'aerial', BasemapConfig> = {
  map: {
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: OPENSTREETMAP_ATTRIBUTION,
    maxZoom: 19,
  },
  aerial: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: ESRI_IMAGERY_ATTRIBUTION,
    maxZoom: 19,
  },
}

/** The 3D view owns its own canvas and therefore has no Leaflet basemap. */
export function basemapForView(view: MapViewMode): BasemapConfig | null {
  return view === '3d' ? null : BASEMAPS[view]
}
