import type { Site } from '@/types/dispatch'
import type { ScenarioDefinition, ScenarioResult } from '@/types/scenario'

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

function result(
  site: Site,
  lossFactor: number,
  values: Record<string, number>,
  response: ScenarioResult['response'],
  responseLabel: string,
  affectedLayer: ScenarioResult['affectedLayer'],
  assumptions: string[],
): ScenarioResult {
  const duration = clamp(values.duration ?? 1, 1, 30)
  const severity = clamp(values.severity ?? 50, 0, 100) / 100
  const baselineLoss = site.economics?.kwh_lost_monthly ?? 0
  const monthlyGeneration = site.series?.actual_vs_expected.reduce((sum, row) => sum + row.actual_kwh, 0) ?? 0
  const generationLossKwh = Math.max(0, Math.round((monthlyGeneration || baselineLoss) * lossFactor * severity * (duration / 30)))
  const tariff = site.tariff_rm_per_kwh || 0
  const rmExposure = Math.max(0, Number((generationLossKwh * tariff).toFixed(2)))
  return {
    generationLossKwh,
    rmExposure,
    confidence: Number((0.55 + (site.detection?.confidence ?? 0.45) * 0.35).toFixed(2)),
    response,
    responseLabel,
    evidenceLevel: 'simulated',
    assumptions,
    affectedLayer,
  }
}

const sharedParameters = (severity = 50, duration = 7): ScenarioDefinition['parameters'] => [
  { id: 'severity', label: 'Severity', min: 10, max: 100, step: 5, unit: '%', defaultValue: severity },
  { id: 'duration', label: 'Duration', min: 1, max: 30, step: 1, unit: 'days', defaultValue: duration },
]

export const scenarioDefinitions: ScenarioDefinition[] = [
  {
    id: 'soiling', title: 'Soiling build-up', group: 'revenue',
    description: 'Estimate the bounded impact of dust or residue accumulating across the array.',
    parameters: sharedParameters(45, 14),
    run: (site, values) => result(site, 0.28, values, 'verify', 'Verify with an inspection pass', 'array', ['Illustrative loss factor: 28% at full severity.', 'Actual soiling requires field confirmation.']),
  },
  {
    id: 'partial-shading', title: 'Partial shading', group: 'revenue',
    description: 'Model a shaded array section during the selected period.',
    parameters: sharedParameters(35, 10),
    run: (site, values) => result(site, 0.2, values, 'verify', 'Verify array obstruction and shading path', 'array', ['Illustrative affected-area factor: 20% at full severity.', 'No roof or obstruction geometry is measured in this dataset.']),
  },
  {
    id: 'inverter-derating', title: 'Inverter derating', group: 'revenue',
    description: 'Model an equipment output cap that persists through the period.',
    parameters: sharedParameters(55, 5),
    run: (site, values) => result(site, 0.36, values, 'dispatch', 'Dispatch after electrical verification', 'equipment', ['Illustrative equipment factor: 36% at full severity.', 'The equipment position is simulated.']),
  },
  {
    id: 'string-underperformance', title: 'String underperformance', group: 'revenue',
    description: 'Model one underperforming string group inside the illustrative array.',
    parameters: sharedParameters(40, 7),
    run: (site, values) => result(site, 0.16, values, 'verify', 'Verify string and connector condition', 'array', ['Illustrative single-group factor: 16% at full severity.', 'String topology is not present in the public artifact.']),
  },
  {
    id: 'thermal-hotspot', title: 'Thermal hotspot', group: 'inspection',
    description: 'Create a bounded thermal inspection scenario for a simulated suspect zone.',
    parameters: sharedParameters(60, 2),
    run: (site, values) => result(site, 0.12, values, 'verify', 'Fly a thermal pass before roof access', 'array', ['Hotspot location and temperature are simulated.', 'Thermal imagery must be captured and reviewed in the field.']),
  },
  {
    id: 'storm-damage', title: 'Storm damage', group: 'inspection',
    description: 'Model a short post-storm inspection event across a bounded array area.',
    parameters: sharedParameters(50, 3),
    run: (site, values) => result(site, 0.24, values, 'escalate', 'Escalate for safety review and site inspection', 'array', ['Physical damage is illustrative only.', 'Safety status requires a qualified field inspection.']),
  },
  {
    id: 'heatwave', title: 'Heatwave stress', group: 'grid',
    description: 'Model environmental heat affecting expected output and equipment margin.',
    parameters: sharedParameters(50, 14),
    run: (site, values) => result(site, 0.1, values, 'monitor', 'Monitor cohort divergence and temperature', 'grid', ['Illustrative heat derate: 10% at full severity.', 'Weather inputs are not a site forecast.']),
  },
  {
    id: 'curtailment', title: 'Grid curtailment', group: 'grid',
    description: 'Model a grid-side reduction that changes economics without changing physical geometry.',
    parameters: sharedParameters(45, 4),
    run: (site, values) => result(site, 0.18, values, 'monitor', 'Monitor grid event and tariff context', 'grid', ['Curtailment is an illustrative scenario.', 'No live grid dispatch signal is connected.']),
  },
]

export function scenarioById(id: string): ScenarioDefinition | undefined {
  return scenarioDefinitions.find((scenario) => scenario.id === id)
}

export function runScenario(site: Site, scenario: ScenarioDefinition, values: Record<string, number>): ScenarioResult {
  return scenario.run(site, values)
}

