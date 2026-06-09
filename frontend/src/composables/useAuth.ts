import { OAUTH_BASE, REDIRECT_URI } from '../config/env'
import { generateVerifier, generateChallenge, generateState } from '../utils/pkce'

export class AuthError extends Error {
  constructor(msg: string) {
    super(msg)
    this.name = 'AuthError'
  }
}

// clientId is not a secret — persist across browser sessions so we reuse the
// same registered OAuth client instead of creating a new one every session.
const LS = {
  clientId: 'adel_client_id',
} as const

// Tokens are sensitive — scope to the browser session only.
const SS = {
  access:    'adel_access_token',
  refresh:   'adel_refresh_token',
  expiresAt: 'adel_token_expires_at',
} as const

const PKCE = {
  verifier:  'adel_pkce_verifier',
  state:     'adel_pkce_state',
  postRoute: 'adel_post_login_route',
} as const

function clearTokens(): void {
  sessionStorage.removeItem(SS.access)
  sessionStorage.removeItem(SS.refresh)
  sessionStorage.removeItem(SS.expiresAt)
}

export function isAuthenticated(): boolean {
  const token = sessionStorage.getItem(SS.access)
  const exp   = Number(sessionStorage.getItem(SS.expiresAt) ?? 0)
  return !!token && exp > Date.now() + 60_000
}

export function hasRefreshToken(): boolean {
  return !!sessionStorage.getItem(SS.refresh)
}

export function getClientId(): string | null {
  return localStorage.getItem(LS.clientId)
}

export async function refreshTokens(): Promise<void> {
  const refreshToken = sessionStorage.getItem(SS.refresh)
  const clientId     = localStorage.getItem(LS.clientId)

  if (!refreshToken || !clientId) {
    clearTokens()
    throw new AuthError('Session expired')
  }

  const res = await fetch(`${OAUTH_BASE}/api/oauth/token`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body:    new URLSearchParams({
      grant_type:    'refresh_token',
      refresh_token: refreshToken,
      client_id:     clientId,
    }),
  })

  if (res.status === 400 || res.status === 401) {
    clearTokens()
    throw new AuthError('Session expired')
  }
  if (!res.ok) throw new AuthError(`Token refresh failed: ${res.statusText}`)

  const data = await res.json() as {
    access_token:  string
    refresh_token: string
    expires_in:    number
  }

  sessionStorage.setItem(SS.access,    data.access_token)
  sessionStorage.setItem(SS.refresh,   data.refresh_token)
  sessionStorage.setItem(SS.expiresAt, String(Date.now() + data.expires_in * 1000))
}

export async function requireAuth(): Promise<string> {
  if (isAuthenticated()) return sessionStorage.getItem(SS.access)!
  if (hasRefreshToken()) {
    await refreshTokens()
    return sessionStorage.getItem(SS.access)!
  }
  throw new AuthError('Not authenticated')
}

export async function registerClient(): Promise<string> {
  const stored = localStorage.getItem(LS.clientId)
  if (stored) return stored

  const res = await fetch(`${OAUTH_BASE}/api/oauth/register`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({
      client_name:                'personal-intelligence-dashboard',
      redirect_uris:              [REDIRECT_URI],
      token_endpoint_auth_method: 'none',
      grant_types:                ['authorization_code', 'refresh_token'],
      response_types:             ['code'],
    }),
  })

  if (!res.ok) throw new AuthError(`Client registration failed: ${res.status}`)

  const data = await res.json() as { client_id: string }
  localStorage.setItem(LS.clientId, data.client_id)
  return data.client_id
}

export async function initiateLogin(intendedRoute = '/'): Promise<void> {
  const clientId  = await registerClient()
  const verifier  = generateVerifier()
  const state     = generateState()
  const challenge = await generateChallenge(verifier)

  sessionStorage.setItem(PKCE.verifier,  verifier)
  sessionStorage.setItem(PKCE.state,     state)
  sessionStorage.setItem(PKCE.postRoute, intendedRoute)

  const params = new URLSearchParams({
    response_type:         'code',
    client_id:             clientId,
    redirect_uri:          REDIRECT_URI,
    code_challenge:        challenge,
    code_challenge_method: 'S256',
    state,
  })

  window.location.href = `${OAUTH_BASE}/api/oauth/authorize?${params}`
}

export function logout(): void {
  clearTokens()
  // Dynamic import avoids circular dep: router imports useAuth, useAuth imports router.
  import('../router/index').then(m => m.default.push('/login'))
}
