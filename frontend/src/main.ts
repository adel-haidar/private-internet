import { createApp } from 'vue'
import './style.css'
import './styles/tokens.css'
import './styles/components.css'
import './styles/health-guide.css'
import './styles/finances.css'
// Initialize theme + locale (sets <html> lang/dir) before mount to avoid flash
import './composables/useTheme'
import './i18n'
import App from './App.vue'
import router from './router'

// Global upgrade-wall handler. The backend returns HTTP 402 from any feature the
// caller's plan doesn't include (ARIA/SIGNAL/STORIES/PULSE media). The route
// guard catches full navigations, but in-page fetches (e.g. background polling)
// could still hit a gate — without this they'd fail silently. Here we send the
// user to the pricing page with context instead. Billing endpoints never 402, so
// they're excluded to avoid loops.
const _origFetch: typeof window.fetch = window.fetch.bind(window)
window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  const res = await _origFetch(input, init)
  if (res.status === 402) {
    try {
      const url =
        typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
      if (url.includes('/api/') && !url.includes('/api/billing/')) {
        const data = (await res.clone().json().catch(() => ({}))) as { feature?: string }
        const feature = data.feature ?? ''
        if (router.currentRoute.value.path !== '/subscribe') {
          router.push(`/subscribe?feature=${encodeURIComponent(feature)}`)
        }
      }
    } catch {
      /* never let the upgrade guard break the original request */
    }
  }
  return res
}

createApp(App).use(router).mount('#app')
