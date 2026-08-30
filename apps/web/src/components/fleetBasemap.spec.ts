import { describe, expect, it } from 'vitest'

import { basemapForView } from './fleetBasemap'

describe('basemapForView', () => {
  it('uses keyless OpenStreetMap tiles for the Map view', () => {
    const config = basemapForView('map')

    expect(config?.url).toBe('https://tile.openstreetmap.org/{z}/{x}/{y}.png')
    expect(config?.url).not.toContain('{s}')
    expect(config?.url).not.toContain('{r}')
    expect(config?.attribution).toContain('https://www.openstreetmap.org/copyright')
    expect(config?.attribution).toContain('OpenStreetMap')
  })

  it('keeps Esri imagery isolated to the Aerial view', () => {
    const config = basemapForView('aerial')

    expect(config?.url).toContain('/World_Imagery/MapServer/tile/{z}/{y}/{x}')
    expect(config?.attribution).toContain('Esri')
  })

  it('does not create a Leaflet basemap for the 3D view', () => {
    expect(basemapForView('3d')).toBeNull()
  })
})
