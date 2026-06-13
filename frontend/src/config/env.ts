// API calls are always relative — proxy in dev, same-origin in prod
export const OAUTH_BASE = ''

// Only REDIRECT_URI needs to be absolute (backend redirects the browser to it)
export const REDIRECT_URI =
  import.meta.env.VITE_REDIRECT_URI ??
  `${window.location.origin}/oauth/callback`

// Backend API base. Dev: relative (vite proxy). Prod: same-origin by default,
// or an explicit base via VITE_API_BASE_URL (e.g. when the dashboard is served
// from a different host than the API).
// Strip trailing /api if present — the secret was historically set to
// https://adel-intelligence.com/api but composables append /api/ themselves.
export const API_BASE: string = import.meta.env.DEV
  ? ''
  : (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/api\/?$/, '')
