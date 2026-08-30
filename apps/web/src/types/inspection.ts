export type InspectionMode = 'guided' | 'explore'
export type BuildingVariant = 'warehouse' | 'commercial' | 'ground-array'
export type WaypointFocus = 'array' | 'obstruction' | 'inverter' | 'string' | 'thermal' | 'damage' | 'environment' | 'grid'

export interface InspectionWaypoint {
  id: string
  label: string
  instruction: string
  position: [number, number, number]
  cameraTarget: [number, number, number]
  focus: WaypointFocus
}

export interface InspectionRoute {
  scenarioId: string
  label: string
  building: BuildingVariant
  visualTreatment: string
  waypoints: InspectionWaypoint[]
}
