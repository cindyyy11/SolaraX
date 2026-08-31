<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { CircleStop, Play, RotateCcw } from '@lucide/vue'
import type { Site } from '@/types/dispatch'
import { evidenceEventsFor } from '@/services/evidenceTimeline'

const props = defineProps<{ site: Site }>()
const events = computed(() => evidenceEventsFor(props.site))
const activeIndex = ref(Math.max(0, events.value.length - 1))
const isPlaying = ref(false)
let timer: ReturnType<typeof setInterval> | undefined

const active = computed(() => events.value[activeIndex.value])
watch(() => events.value.length, (length, previous) => { if (!isPlaying.value && length > previous) activeIndex.value=length-1 })
function stop() { if (timer) clearInterval(timer); timer=undefined; isPlaying.value=false }
function replay() { stop(); activeIndex.value=0; if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return; isPlaying.value=true; timer=setInterval(() => { if (activeIndex.value >= events.value.length - 1) return stop(); activeIndex.value += 1 }, 1250) }
function reset() { stop(); activeIndex.value=Math.max(0,events.value.length-1) }
onBeforeUnmount(stop)
</script>

<template>
  <section class="timeline card card--interactive" aria-labelledby="timeline-title">
    <header class="timeline__header"><div><h2 id="timeline-title">Evidence timeline</h2><p>Measured, inferred and simulated events remain distinct throughout the decision.</p></div><div class="timeline__actions"><button v-if="!isPlaying" type="button" @click="replay"><Play :size="14" aria-hidden="true" /> Replay incident</button><button v-else type="button" @click="stop"><CircleStop :size="14" aria-hidden="true" /> Stop</button><button type="button" aria-label="Reset incident replay" @click="reset"><RotateCcw :size="14" aria-hidden="true" /></button></div></header>
    <div v-if="events.length" class="timeline__body">
      <ol class="timeline__events">
        <li v-for="(event,index) in events" :key="event.id"><button type="button" :class="{ active:activeIndex===index, passed:activeIndex>index }" :aria-current="activeIndex===index ? 'step' : undefined" @click="stop(); activeIndex=index"><i></i><span><small>{{ new Date(event.timestamp).toLocaleDateString('en-MY',{ day:'numeric',month:'short',year:'numeric' }) }}</small><strong>{{ event.title }}</strong><em>{{ event.evidenceLevel }}</em></span></button></li>
      </ol>
      <article v-if="active" class="timeline__focus" aria-live="polite"><span :class="`level--${active.evidenceLevel}`">{{ active.evidenceLevel }}</span><h3>{{ active.title }}</h3><p>{{ active.detail }}</p><dl><div><dt>Status</dt><dd>{{ active.status }}</dd></div><div><dt>Confidence</dt><dd>{{ active.confidence === undefined ? 'Not supplied' : `${Math.round(active.confidence * 100)}%` }}</dd></div><div><dt>Source</dt><dd>{{ active.sourceRef }}</dd></div></dl></article>
    </div>
    <p v-else class="timeline__empty">No evidence events are available for this site yet.</p>
  </section>
</template>

<style scoped>
.timeline { overflow:hidden; }
.timeline__header { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; padding:1.1rem 1.25rem; border-bottom:1px solid var(--border-hairline); }
.timeline__header h2 { margin:0; font-family:var(--font-display); font-size:clamp(1.2rem,2vw,1.55rem); letter-spacing:-.03em; }.timeline__header p { margin:.35rem 0 0; color:var(--text-secondary); font-size:.75rem; }
.timeline__actions { display:flex; gap:.3rem; }.timeline__actions button { min-height:40px; display:inline-flex; align-items:center; justify-content:center; gap:.35rem; padding:.5rem .65rem; color:var(--text-secondary); background:var(--surface-2); border:1px solid var(--border-hairline); border-radius:var(--radius-sm); font:inherit; font-size:.67rem; cursor:pointer; }
.timeline__body { display:grid; grid-template-columns:minmax(260px,.8fr) minmax(0,1.2fr); min-height:260px; }
.timeline__events { margin:0; padding:1rem 1.1rem; list-style:none; border-right:1px solid var(--border-hairline); }.timeline__events li { position:relative; }.timeline__events li:not(:last-child)::after { content:''; position:absolute; left:7px; top:26px; bottom:-6px; width:1px; background:var(--baseline); }
.timeline__events button { width:100%; min-height:58px; display:grid; grid-template-columns:16px minmax(0,1fr); gap:.6rem; padding:.45rem; text-align:left; color:var(--text-secondary); background:transparent; border:0; border-radius:var(--radius-sm); font:inherit; cursor:pointer; }.timeline__events button:hover,.timeline__events button.active { background:var(--surface-selected); }.timeline__events i { position:relative; z-index:1; width:15px; height:15px; margin-top:.2rem; border:2px solid var(--baseline); border-radius:50%; background:var(--surface-1); }.timeline__events button.passed i,.timeline__events button.active i { border-color:var(--action-text); background:var(--action-fill); }
.timeline__events small,.timeline__events strong,.timeline__events em { display:block; }.timeline__events small { color:var(--text-muted); font-size:.58rem; }.timeline__events strong { margin-top:.12rem; color:var(--text-primary); font-size:.72rem; }.timeline__events em { margin-top:.18rem; color:var(--text-muted); font-size:.56rem; font-style:normal; text-transform:uppercase; letter-spacing:.06em; }
.timeline__focus { display:flex; flex-direction:column; justify-content:center; padding:1.4rem; }.timeline__focus > span { align-self:flex-start; padding:.22rem .38rem; border-radius:var(--radius-sm); font-size:.56rem; font-weight:800; letter-spacing:.07em; text-transform:uppercase; }.level--measured { color:#173126; background:#9ce8b9; }.level--inferred { color:#3b2c12; background:#f0c883; }.level--simulated { color:#fff; background:#596a65; }.timeline__focus h3 { margin:.65rem 0 .35rem; font-family:var(--font-display); font-size:clamp(1.25rem,2.4vw,1.8rem); letter-spacing:-.03em; }.timeline__focus > p { max-width:65ch; margin:0; color:var(--text-secondary); font-size:.8rem; line-height:1.55; }.timeline__focus dl { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.5rem; margin:1rem 0 0; }.timeline__focus dl div { min-width:0; padding-top:.5rem; border-top:1px solid var(--border-hairline); }.timeline__focus dt { color:var(--text-muted); font-size:.58rem; }.timeline__focus dd { margin:.2rem 0 0; font-size:.66rem; overflow-wrap:anywhere; }.timeline__empty { margin:0; padding:1.5rem; color:var(--text-muted); text-align:center; }
@media (max-width:760px) { .timeline__header { flex-direction:column; }.timeline__actions { width:100%; }.timeline__actions button:first-child { flex:1; }.timeline__body { grid-template-columns:1fr; }.timeline__events { border-right:0; border-bottom:1px solid var(--border-hairline); }.timeline__focus dl { grid-template-columns:1fr; } }
</style>
