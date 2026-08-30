<script setup lang="ts">
import { computed } from 'vue'
import { Activity, ArrowRight, Clock3 } from '@lucide/vue'
import type { Site } from '@/types/dispatch'
import { calculateRecovery } from '@/services/recoveryEngine'

const props = defineProps<{ site: Site }>()

const recovery = computed(() => calculateRecovery({
  siteId:props.site.site_id,
  workOrderId:`pending-${props.site.site_id}`,
  tariffRmPerKwh:props.site.tariff_rm_per_kwh,
  interventionCostRm:0,
  projectedMonthlyRecoveryKwh:props.site.economics?.kwh_lost_monthly ?? 0,
  baselinePerformanceRatio:Math.max(0, 1 - (props.site.economics?.loss_pct_of_expected ?? 0) / 100),
  postWorkObservations:[],
}))

const isEligible = computed(() => props.site.status === 'dispatch' && Boolean(props.site.economics))
</script>

<template>
  <section class="recovery" aria-labelledby="recovery-title">
    <header class="recovery__header">
      <div>
        <h2 id="recovery-title">Recovery tracker</h2>
        <p>Connect this month’s decision to post-maintenance proof of value.</p>
      </div>
      <span class="recovery__status"><Clock3 :size="14" aria-hidden="true" /> {{ isEligible ? 'Verification not started' : 'Monitoring only' }}</span>
    </header>

    <div class="recovery__body">
      <div class="recovery__forecast">
        <span>Projected recoverable value</span>
        <strong>RM {{ recovery.projectedRecoveryRm.toLocaleString() }}<small>/month</small></strong>
        <p>{{ recovery.projectedRecoveryKwh.toLocaleString() }} kWh currently at risk. This is a projection, not recovered generation.</p>
      </div>

      <ol class="recovery__flow" aria-label="Recovery verification workflow">
        <li class="complete"><span>1</span><div><strong>Loss detected</strong><small>Electrical evidence available</small></div></li>
        <li :class="{ complete: isEligible }"><span>2</span><div><strong>Dispatch decision</strong><small>{{ isEligible ? 'Work order can be issued' : 'Continue monitoring' }}</small></div></li>
        <li><span>3</span><div><strong>Work completed</strong><small>Completion date required</small></div></li>
        <li><span>4</span><div><strong>Recovery verified</strong><small>Minimum 7 valid post-work days</small></div></li>
      </ol>

      <aside class="recovery__requirements">
        <Activity :size="18" aria-hidden="true" />
        <div><strong>What makes recovery verifiable?</strong><p>A completed work order, a documented intervention cost, and at least seven valid days of expected-versus-actual generation.</p></div>
        <RouterLink v-if="isEligible" :to="`/site/${site.site_id}/work-order`">Prepare work order <ArrowRight :size="14" aria-hidden="true" /></RouterLink>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.recovery { margin:1.75rem 0; overflow:hidden; color:#eff5f2; background:#13211d; border-radius:var(--radius-lg); box-shadow:0 18px 42px rgba(9,22,18,.16); }
.recovery__header { display:flex; align-items:flex-start; justify-content:space-between; gap:1.25rem; padding:1.1rem 1.25rem; border-bottom:1px solid rgba(255,255,255,.09); }
.recovery__header h2 { margin:0; font-family:var(--font-display); font-size:clamp(1.2rem,2vw,1.55rem); letter-spacing:-.03em; }
.recovery__header p { margin:.35rem 0 0; color:#9fb0aa; font-size:.78rem; }
.recovery__status { min-height:34px; display:inline-flex; align-items:center; gap:.4rem; padding:.4rem .6rem; color:#f2c47f; background:rgba(242,196,127,.1); border-radius:var(--radius-sm); font-size:.66rem; font-weight:700; white-space:nowrap; }
.recovery__body { display:grid; grid-template-columns:minmax(240px,.65fr) minmax(0,1.35fr); }
.recovery__forecast { display:flex; flex-direction:column; justify-content:center; padding:1.4rem 1.25rem; border-right:1px solid rgba(255,255,255,.09); }
.recovery__forecast > span { color:#96aaa3; font-size:.64rem; }
.recovery__forecast > strong { margin:.3rem 0; font-family:var(--font-display); font-size:clamp(1.8rem,4vw,3rem); letter-spacing:-.04em; }
.recovery__forecast strong small { margin-left:.25rem; color:#96aaa3; font:600 .68rem var(--font-sans); letter-spacing:0; }
.recovery__forecast p { max-width:38ch; margin:.2rem 0 0; color:#aebdb8; font-size:.7rem; line-height:1.5; }
.recovery__flow { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:0; margin:0; padding:1.35rem 1.15rem; list-style:none; }
.recovery__flow li { position:relative; display:flex; align-items:flex-start; gap:.5rem; min-width:0; color:#789087; }
.recovery__flow li:not(:last-child)::after { content:''; position:absolute; left:30px; right:5px; top:13px; height:1px; background:#344941; }
.recovery__flow li > span { position:relative; z-index:1; flex:0 0 auto; display:grid; place-items:center; width:28px; height:28px; color:#9eb0aa; background:#21332d; border-radius:50%; font-size:.62rem; }
.recovery__flow li.complete > span { color:#14241e; background:#7be0a5; }
.recovery__flow strong,.recovery__flow small { display:block; padding-right:.35rem; overflow-wrap:anywhere; }
.recovery__flow strong { margin-top:.05rem; color:#dce7e2; font-size:.68rem; }
.recovery__flow small { margin-top:.2rem; font-size:.6rem; line-height:1.35; }
.recovery__requirements { grid-column:1 / -1; display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:.75rem; padding:.85rem 1.25rem; color:#dce7e2; background:#0e1916; border-top:1px solid rgba(255,255,255,.09); }
.recovery__requirements > svg { color:#7be0a5; }
.recovery__requirements strong { display:block; font-size:.72rem; }
.recovery__requirements p { margin:.2rem 0 0; color:#91a39d; font-size:.65rem; line-height:1.45; }
.recovery__requirements a { min-height:40px; display:inline-flex; align-items:center; gap:.35rem; padding:.5rem .65rem; color:#172921; background:#7be0a5; border-radius:var(--radius-sm); font-size:.68rem; font-weight:750; text-decoration:none; white-space:nowrap; }
@media (max-width:850px) { .recovery__body { grid-template-columns:1fr; } .recovery__forecast { border-right:0; border-bottom:1px solid rgba(255,255,255,.09); } }
@media (max-width:620px) { .recovery__header { flex-direction:column; } .recovery__status { width:100%; } .recovery__flow { grid-template-columns:1fr; gap:.7rem; } .recovery__flow li:not(:last-child)::after { left:13px; right:auto; top:28px; bottom:-9px; width:1px; height:auto; } .recovery__requirements { grid-template-columns:auto 1fr; } .recovery__requirements a { grid-column:1 / -1; justify-content:center; } }
</style>
