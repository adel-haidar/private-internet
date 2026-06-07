// API calls are always relative — proxy in dev, same-origin in prod
export const OAUTH_BASE = ''

// Only REDIRECT_URI needs to be absolute (backend redirects the browser to it)
export const REDIRECT_URI =
  import.meta.env.VITE_REDIRECT_URI ??
  `${window.location.origin}/oauth/callback`
