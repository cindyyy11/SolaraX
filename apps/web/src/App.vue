<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { Activity, ChartNoAxesCombined, LayoutDashboard } from '@lucide/vue'
import BrandLogo from '@/components/BrandLogo.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import SiteSearch from '@/components/SiteSearch.vue'
</script>

<template>
  <a class="skip-link" href="#main-content">Skip to main content</a>
  <div class="app-shell">
    <aside class="app-rail" aria-label="Primary navigation">
      <RouterLink to="/" class="app-rail__brand" aria-label="SolaraX — dispatch home">
        <BrandLogo :size="34" mark-only />
      </RouterLink>
      <nav class="app-rail__nav" aria-label="Site sections">
        <RouterLink to="/" class="app-rail__link" aria-label="Dispatch">
          <LayoutDashboard :size="20" aria-hidden="true" /><span>Dispatch</span>
        </RouterLink>
        <RouterLink to="/fleet-health" class="app-rail__link" aria-label="Fleet performance">
          <ChartNoAxesCombined :size="20" aria-hidden="true" /><span>Performance</span>
        </RouterLink>
        <SiteSearch />
      </nav>
      <div class="app-rail__footer">
        <span class="app-rail__system" title="Fleet analysis is available">
          <Activity :size="17" aria-hidden="true" /><span>System ready</span>
        </span>
        <ThemeToggle />
      </div>
    </aside>

    <header class="mobile-header">
      <RouterLink to="/" class="mobile-header__brand" aria-label="SolaraX — dispatch home">
        <BrandLogo :size="30" mark-only />
      </RouterLink>
      <nav class="mobile-header__nav" aria-label="Primary navigation">
        <RouterLink to="/">Dispatch</RouterLink>
        <RouterLink to="/fleet-health">Fleet</RouterLink>
      </nav>
      <SiteSearch mobile />
      <ThemeToggle />
    </header>

    <div class="app-shell__content"><RouterView /></div>
  </div>
</template>

<style scoped>
.skip-link {
  position: fixed;
  top: 0.75rem;
  left: 0.75rem;
  z-index: var(--z-skip-link);
  padding: 0.75rem 1rem;
  color: var(--action-ink);
  background: var(--action-fill);
  border-radius: var(--radius-md);
  font-weight: 700;
  text-decoration: none;
  transform: translateY(-160%);
  transition: transform var(--duration-fast) var(--ease-out);
}
.skip-link:focus {
  transform: translateY(0);
}
.app-shell {
  min-height: 100vh;
  padding-left: 6.5rem;
}
.app-rail {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: var(--z-nav);
  display: flex;
  width: 6.5rem;
  flex-direction: column;
  align-items: center;
  padding: 1.1rem 0.7rem;
  background: var(--nav-surface);
  border-right: 1px solid var(--nav-border);
}
.app-rail__brand {
  display: grid;
  width: 3.25rem;
  height: 3.25rem;
  place-items: center;
  color: var(--nav-text-strong);
  border-radius: 14px;
  --brand-ink: var(--nav-text-strong);
}
.app-rail__nav {
  display: flex;
  width: 100%;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 2.1rem;
}
.app-rail__link {
  display: flex;
  min-height: 4.25rem;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  color: var(--nav-text);
  border: 1px solid transparent;
  border-radius: 14px;
  font-family: var(--font-display);
  font-size: 0.68rem;
  font-weight: 650;
  text-decoration: none;
  transition:
    color var(--duration-fast) var(--ease-out),
    background-color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}
.app-rail__link:hover {
  color: var(--nav-text-strong);
  background: var(--nav-hover);
}
.app-rail__link.router-link-exact-active {
  color: var(--nav-active-text);
  background: var(--nav-active);
  border-color: var(--nav-active-border);
}
.app-rail__footer {
  display: flex;
  width: 100%;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  margin-top: auto;
}
.app-rail__system {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  color: var(--nav-text);
  font-size: 0.6rem;
  text-align: center;
}
.app-rail__system :deep(svg) {
  color: var(--signal-live);
}
.mobile-header {
  display: none;
}
.app-shell__content {
  min-width: 0;
}
@media (max-width: 760px) {
  .app-shell {
    padding-left: 0;
  }
  .app-rail {
    display: none;
  }
  .app-shell__content {
    margin-top: 4.2rem;
  }
  .mobile-header {
    position: fixed;
    inset: 0 0 auto;
    z-index: var(--z-nav);
    display: grid;
    grid-template-columns: auto 1fr auto;
    min-height: 4.2rem;
    align-items: center;
    gap: 0.5rem;
    padding: 0.55rem 1rem;
    background: color-mix(in srgb, var(--page-plane) 92%, transparent);
    border-bottom: 1px solid var(--border-hairline);
    backdrop-filter: blur(16px);
  }
  .mobile-header__brand {
    display: inline-flex;
    min-width: 0;
  }
  .mobile-header__nav {
    display: flex;
    justify-content: flex-end;
    gap: 0.25rem;
  }
  .mobile-header__nav a {
    display: inline-flex;
    min-height: 2.75rem;
    align-items: center;
    padding: 0 0.65rem;
    color: var(--text-secondary);
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    font-size: 0.78rem;
    font-weight: 650;
    text-decoration: none;
  }
  .mobile-header__nav a.router-link-exact-active {
    color: var(--action-text);
    background: var(--surface-selected);
    border-color: var(--action-text);
  }
  .mobile-header :deep(.theme) {
    display: none;
  }
  .mobile-header :deep(.search-launch) {
    color: var(--text-secondary);
    border-color: var(--border-hairline);
  }
}
@media (max-width: 430px) {
  .mobile-header__nav a {
    padding: 0 0.5rem;
    font-size: 0.72rem;
  }
}
</style>
