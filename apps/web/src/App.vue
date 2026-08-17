<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app">
    <nav class="app__nav">
      <RouterLink to="/" class="app__brand">SolaraX</RouterLink>
      <span class="app__tagline">Fleet yield assurance for distributed C&amp;I solar</span>
      <span class="app__links">
        <RouterLink to="/">Dispatch</RouterLink>
        <RouterLink to="/fleet-health">Fleet health &amp; ROI</RouterLink>
      </span>
    </nav>

    <RouterView />
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
}

.app__nav {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.75rem;
  max-width: 1280px;
  margin: 0 auto;
  padding: 1rem 1.5rem 0;
}

.app__brand {
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--text-primary);
  text-decoration: none;
}

.app__tagline {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.app__links {
  margin-left: auto;
  display: flex;
  gap: 1rem;
  font-size: 0.82rem;
}

.app__links a {
  color: var(--text-secondary);
  text-decoration: none;
  padding-bottom: 2px;
  border-bottom: 2px solid transparent;
}

.app__links a.router-link-exact-active {
  color: var(--text-primary);
  border-bottom-color: var(--text-primary);
}
</style>
