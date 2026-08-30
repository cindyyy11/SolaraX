<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import BrandLogo from '@/components/BrandLogo.vue'
</script>

<template>
  <div class="app">
    <nav class="app__nav">
      <div class="app__nav-inner">
        <RouterLink to="/" class="app__brand" aria-label="SolaraX — home">
          <BrandLogo :size="30" />
        </RouterLink>
        <span class="app__tagline">Fleet yield assurance for distributed C&amp;I solar</span>
        <span class="app__links">
          <RouterLink to="/">Dispatch</RouterLink>
          <RouterLink to="/fleet-health">Fleet health &amp; ROI</RouterLink>
        </span>
      </div>
    </nav>

    <RouterView />
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
}

/*
 * The nav is the one place brand navy gets to be a SURFACE rather than an
 * accent — a single, deliberate use of --brand-navy as a background, sitting
 * above the page rather than floating on it. Everywhere else in the product
 * the brand pair stays in the "action" role (see theme.css); this is the
 * exception, and there is exactly one of it.
 */
.app__nav {
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--brand-navy);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.app__nav-inner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.9rem;
  max-width: 1280px;
  margin: 0 auto;
  padding: 0.7rem 1.5rem;
}

.app__brand {
  display: inline-flex;
  text-decoration: none;
  border-radius: var(--radius-sm);
  /* BrandLogo's mark and wordmark both read `--brand-ink` directly (CSS custom
     properties cross component boundaries through the DOM, so no :deep is
     needed). Pinned light here because the mark sits on the navy nav surface
     itself, not on the page background --brand-ink normally tracks. */
  --brand-ink: #f2f4f8;
}

.app__tagline {
  font-size: 0.78rem;
  color: rgba(242, 244, 248, 0.62);
}

.app__links {
  margin-left: auto;
  display: flex;
  gap: 1.4rem;
  font-size: 0.82rem;
}

.app__links a {
  display: inline-flex;
  align-items: center;
  height: 2.75rem;
  color: rgba(242, 244, 248, 0.72);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  transition:
    color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}

.app__links a:hover {
  color: #f2f4f8;
}

.app__links a.router-link-exact-active {
  color: #f2f4f8;
  font-weight: 600;
  border-bottom-color: var(--brand-solar);
}

@media (max-width: 640px) {
  .app__tagline {
    display: none;
  }
}
</style>
