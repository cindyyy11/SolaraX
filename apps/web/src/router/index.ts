import { createRouter, createWebHistory } from 'vue-router'
import DispatchView from '../views/DispatchView.vue'
import NotFoundView from '../views/NotFoundView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      // Screen 1 — the landing screen. PRD v2 section 4.
      path: '/',
      name: 'dispatch',
      component: DispatchView,
    },
    {
      // Screen 2 — Site Detail. Lazy so the cohort chart's ECharts bundle
      // is not paid for on the landing screen.
      path: '/site/:siteId',
      name: 'site-detail',
      component: () => import('../views/SiteDetailView.vue'),
    },
    {
      // Screen 3 — Work Order. Exportable card handed to a technician.
      path: '/site/:siteId/work-order',
      name: 'work-order',
      component: () => import('../views/WorkOrderView.vue'),
    },
    {
      // Screen 4 — Fleet Health & ROI. The screen a P&L owner opens.
      path: '/fleet-health',
      name: 'fleet-health',
      component: () => import('../views/FleetHealthView.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFoundView,
    },
  ],
})

export default router
