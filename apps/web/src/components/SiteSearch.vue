<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, X } from '@lucide/vue'
import { formatCapacity, loadDispatch } from '@/services/api'
import type { Site } from '@/types/dispatch'

defineProps<{ mobile?: boolean }>()
const router = useRouter()
const dialog = ref<HTMLDialogElement | null>(null)
const query = ref('')
const sites = ref<Site[]>([])
const loading = ref(false)

const matches = computed(() => {
  const needle = query.value.trim().toLowerCase()
  if (!needle) return sites.value.slice(0, 6)
  return sites.value
    .filter((site) => `${site.name} ${site.site_id} ${site.address}`.toLowerCase().includes(needle))
    .slice(0, 8)
})

async function open(): Promise<void> {
  dialog.value?.showModal()
  if (sites.value.length) return
  loading.value = true
  try {
    sites.value = (await loadDispatch()).dispatch.sites
  } finally {
    loading.value = false
  }
}

function choose(siteId: string): void {
  dialog.value?.close()
  query.value = ''
  router.push({ name: 'site-detail', params: { siteId } })
}
</script>

<template>
  <button
    type="button"
    class="search-launch"
    :class="{ 'search-launch--mobile': mobile }"
    aria-label="Search fleet sites"
    @click="open"
  >
    <Search :size="19" aria-hidden="true" /><span>Search</span>
  </button>
  <dialog ref="dialog" class="search-dialog" @click.self="dialog?.close()">
    <header>
      <div>
        <h2>Find a fleet site</h2>
        <p>Search by name, site ID, or address.</p>
      </div>
      <button type="button" aria-label="Close search" @click="dialog?.close()">
        <X :size="18" aria-hidden="true" />
      </button>
    </header>
    <label class="search-field"
      ><Search :size="18" aria-hidden="true" /><span class="sr-only">Search fleet sites</span
      ><input v-model="query" type="search" placeholder="Start typing a site name…" autofocus
    /></label>
    <p v-if="loading" class="search-state">Loading fleet index…</p>
    <ul v-else-if="matches.length" class="search-results">
      <li v-for="site in matches" :key="site.site_id">
        <button type="button" @click="choose(site.site_id)">
          <span
            ><strong>{{ site.name }}</strong
            ><small>{{ site.site_id }} · {{ site.address }}</small></span
          ><span>{{ formatCapacity(site.capacity_kwp) }}</span>
        </button>
      </li>
    </ul>
    <p v-else class="search-state">No site matches “{{ query }}”.</p>
  </dialog>
</template>

<style scoped>
.search-launch {
  display: flex;
  min-height: 4.25rem;
  width: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  color: var(--nav-text);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 14px;
  font: 650 0.68rem var(--font-display);
  cursor: pointer;
}
.search-launch:hover {
  color: var(--nav-text-strong);
  background: var(--nav-hover);
}
.search-launch--mobile {
  min-height: 2.75rem;
  width: 2.75rem;
}
.search-launch--mobile span {
  display: none;
}
.search-dialog {
  width: min(38rem, calc(100vw - 2rem));
  padding: 0;
  color: var(--text-primary);
  background: var(--surface-1);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.36);
}
.search-dialog::backdrop {
  background: rgba(4, 10, 8, 0.58);
  backdrop-filter: blur(3px);
}
.search-dialog header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1rem 0.75rem;
}
.search-dialog h2 {
  margin: 0;
  font-size: 1.05rem;
}
.search-dialog p {
  margin: 0.25rem 0 0;
  color: var(--text-muted);
  font-size: 0.72rem;
}
.search-dialog header button {
  display: grid;
  width: 2.5rem;
  height: 2.5rem;
  place-items: center;
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  cursor: pointer;
}
.search-field {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin: 0 1rem;
  padding: 0 0.75rem;
  background: var(--surface-2);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}
.search-field input {
  width: 100%;
  min-height: 3rem;
  color: var(--text-primary);
  background: transparent;
  border: 0;
  outline: 0;
  font: inherit;
}
.search-results {
  margin: 0.75rem 0 0;
  padding: 0 1rem 1rem;
  list-style: none;
}
.search-results li + li {
  border-top: 1px solid var(--border-hairline);
}
.search-results button {
  display: flex;
  width: 100%;
  min-height: 3.8rem;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 0.25rem;
  color: var(--text-primary);
  text-align: left;
  background: transparent;
  border: 0;
  cursor: pointer;
}
.search-results button:hover strong {
  color: var(--action-text);
}
.search-results button > span {
  display: flex;
  min-width: 0;
  flex-direction: column;
}
.search-results strong {
  overflow: hidden;
  font-size: 0.8rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.search-results small {
  overflow: hidden;
  color: var(--text-muted);
  font-size: 0.66rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.search-results button > span:last-child {
  flex: none;
  color: var(--text-secondary);
  font-size: 0.68rem;
}
.search-state {
  padding: 1rem !important;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
