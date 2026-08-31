/**
 * Judge Mode — a guided walk through the same operator workflow the design
 * spec defines, using the same routes, data and state as Operator Mode. It
 * never introduces a separate business value or a fabricated site; every
 * step routes to a real screen and, where a step needs a subject site, to
 * the highest-ranked real site currently in the dispatch artifact.
 *
 * docs/superpowers/specs/2026-08-30-solarax-closed-loop-operations-intelligence-design.md
 * — "Operator workflow" and "Judge Mode cannot introduce separate business
 * values or unsupported customer claims."
 */
import { reactive, readonly } from 'vue'
import router from '@/router'
import { loadDispatch, sitesByStatus } from './api'

export interface JudgeStep {
  id: string
  title: string
  description: string
  path: string
}

/** Pure and testable: the eight-step operator workflow, resolved against a
 * real (possibly absent) subject site id. No step description names a
 * figure — the screen it routes to carries the real numbers. */
export function judgeSteps(siteId: string | null): JudgeStep[] {
  const sitePath = (suffix = '') => (siteId ? `/site/${siteId}${suffix}` : '/')
  return [
    {
      id: 'divergence',
      title: 'Review measured divergence and economic exposure',
      description: 'The Dispatch list ranks sites by money at risk, computed from the sensor-free baseline and peer benchmark.',
      path: '/',
    },
    {
      id: 'compare',
      title: 'Compare monitored and dispatched outcomes',
      description: 'Dispatch, monitor and healthy counts, and the visits avoided this month.',
      path: '/',
    },
    {
      id: 'scenario',
      title: 'Apply a bounded scenario',
      description: 'Run a labelled what-if in the Scenario Lab without changing the measured dispatch record.',
      path: sitePath(),
    },
    {
      id: 'inspect',
      title: 'Inspect the affected layer and scenario-specific drone route',
      description: 'The digital twin and inspection route respond to the scenario just applied.',
      path: sitePath(),
    },
    {
      id: 'evidence',
      title: 'Review CV or field evidence',
      description: 'Corroborating imagery evidence, and the evidence timeline connecting every signal so far.',
      path: sitePath(),
    },
    {
      id: 'resilience',
      title: 'Assess relevant resilience indicators',
      description: 'Six resilience categories, each traced to a real signal or reported as not connected.',
      path: '/resilience',
    },
    {
      id: 'work-order',
      title: 'Confirm the operational decision and generate a work order',
      description: 'The printable work order a technician takes into the field.',
      path: sitePath('/work-order'),
    },
    {
      id: 'recovery',
      title: 'Verify recovery when post-work telemetry becomes sufficient',
      description: 'Recovery stays "pending" honestly until enough post-work days exist — never a fabricated verified figure.',
      path: sitePath(),
    },
  ]
}

const state = reactive({
  active: false,
  index: 0,
  siteId: null as string | null,
  steps: judgeSteps(null),
})

async function resolveSubjectSite(): Promise<string | null> {
  try {
    const { dispatch } = await loadDispatch()
    const candidate = sitesByStatus(dispatch, 'dispatch')[0] ?? sitesByStatus(dispatch, 'monitor')[0] ?? dispatch.sites[0]
    return candidate?.site_id ?? null
  } catch {
    return null
  }
}

export const judgeModeState = readonly(state)

export async function enterJudgeMode(): Promise<void> {
  state.siteId = await resolveSubjectSite()
  state.steps = judgeSteps(state.siteId)
  state.active = true
  state.index = 0
  await router.push(state.steps[0]!.path)
}

export function exitJudgeMode(): void {
  state.active = false
}

export async function goToJudgeStep(index: number): Promise<void> {
  if (index < 0 || index >= state.steps.length) return
  state.index = index
  await router.push(state.steps[index]!.path)
}

export function nextJudgeStep(): Promise<void> {
  return goToJudgeStep(state.index + 1)
}

export function previousJudgeStep(): Promise<void> {
  return goToJudgeStep(state.index - 1)
}
