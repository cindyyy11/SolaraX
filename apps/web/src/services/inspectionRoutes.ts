import type { InspectionRoute } from '@/types/inspection'

const route = (definition: InspectionRoute) => definition

export const inspectionRoutes: Record<string, InspectionRoute> = {
  soiling: route({ scenarioId:'soiling', label:'Full-array serpentine survey', building:'warehouse', visualTreatment:'dust', waypoints:[
    { id:'soil-north', label:'North rows', instruction:'Compare residue coverage across the first panel rows.', position:[-3,3,3], cameraTarget:[-2,0,0], focus:'array' },
    { id:'soil-centre', label:'Centre sweep', instruction:'Check whether coverage is uniform or concentrated near drainage paths.', position:[1,2,2.5], cameraTarget:[0,0,0], focus:'array' },
    { id:'soil-south', label:'South rows', instruction:'Confirm whether cleaning access and runoff explain the projected pattern.', position:[3,-2,2.4], cameraTarget:[2,-1,0], focus:'array' },
  ]}),
  'partial-shading': route({ scenarioId:'partial-shading', label:'Obstruction perimeter pass', building:'commercial', visualTreatment:'shadow', waypoints:[
    { id:'shade-edge', label:'Shadow edge', instruction:'Inspect the projected obstruction boundary across the array.', position:[-3,2,3], cameraTarget:[-2,0,0], focus:'obstruction' },
    { id:'shade-source', label:'Obstruction source', instruction:'Verify the illustrative source before attributing production loss.', position:[2,3,3], cameraTarget:[2,1,0], focus:'obstruction' },
  ]}),
  'inverter-derating': route({ scenarioId:'inverter-derating', label:'Equipment verification pass', building:'warehouse', visualTreatment:'equipment-warning', waypoints:[
    { id:'inv-02', label:'Inverter 02', instruction:'Check alarms, temperature, ventilation and output limit state.', position:[4,0,1.7], cameraTarget:[3,0,.5], focus:'inverter' },
    { id:'inv-feed', label:'Array feed', instruction:'Compare upstream array flow before dispatching electrical work.', position:[2,1,2], cameraTarget:[1,0,0], focus:'inverter' },
  ]}),
  'string-underperformance': route({ scenarioId:'string-underperformance', label:'Row-following string trace', building:'warehouse', visualTreatment:'string-loss', waypoints:[
    { id:'string-start', label:'String origin', instruction:'Trace the simulated string from its first module group.', position:[-3,-2,2], cameraTarget:[-2,-1,0], focus:'string' },
    { id:'string-mid', label:'Connector zone', instruction:'Inspect connector continuity along the weakened row.', position:[0,-1,1.8], cameraTarget:[0,-1,0], focus:'string' },
    { id:'string-end', label:'Combiner end', instruction:'Compare the end-of-string response before field verification.', position:[3,-1,2], cameraTarget:[2,-1,0], focus:'string' },
  ]}),
  'thermal-hotspot': route({ scenarioId:'thermal-hotspot', label:'Close thermal orbit', building:'commercial', visualTreatment:'thermal', waypoints:[
    { id:'thermal-wide', label:'Thermal overview', instruction:'Establish surrounding module temperature before close inspection.', position:[0,4,4], cameraTarget:[0,0,0], focus:'thermal' },
    { id:'thermal-close', label:'Suspect module', instruction:'Verify the simulated hotspot with calibrated thermal imagery.', position:[1,1,1.4], cameraTarget:[1,0,0], focus:'thermal' },
  ]}),
  'storm-damage': route({ scenarioId:'storm-damage', label:'Safety perimeter and damage sweep', building:'commercial', visualTreatment:'storm', waypoints:[
    { id:'storm-perimeter', label:'Safety perimeter', instruction:'Check access hazards before approaching the array.', position:[-4,4,4], cameraTarget:[0,0,0], focus:'damage' },
    { id:'storm-zone', label:'Damage zone', instruction:'Document displaced or fractured modules from a safe distance.', position:[1,2,2], cameraTarget:[1,0,0], focus:'damage' },
    { id:'storm-drainage', label:'Roof drainage', instruction:'Inspect debris and standing-water risk after the event.', position:[3,-2,2.5], cameraTarget:[2,-2,0], focus:'damage' },
  ]}),
  heatwave: route({ scenarioId:'heatwave', label:'High-altitude thermal overview', building:'ground-array', visualTreatment:'heat', waypoints:[
    { id:'heat-array', label:'Array temperature', instruction:'Compare heat stress across the full illustrative array.', position:[0,5,6], cameraTarget:[0,0,0], focus:'environment' },
    { id:'heat-equipment', label:'Equipment margin', instruction:'Review inverter thermal margin before changing maintenance priority.', position:[4,2,3], cameraTarget:[3,0,0], focus:'environment' },
  ]}),
  curtailment: route({ scenarioId:'curtailment', label:'Inverter-to-grid trace', building:'ground-array', visualTreatment:'grid-cap', waypoints:[
    { id:'grid-inverter', label:'Inverter output', instruction:'Confirm whether the reduction begins after array conversion.', position:[3,1,2], cameraTarget:[2,0,0], focus:'grid' },
    { id:'grid-boundary', label:'Grid boundary', instruction:'Check the simulated export constraint and event timing.', position:[5,-1,2.5], cameraTarget:[4,-1,0], focus:'grid' },
  ]}),
}

export function inspectionRouteFor(scenarioId: string): InspectionRoute {
  return inspectionRoutes[scenarioId] ?? inspectionRoutes.soiling!
}
