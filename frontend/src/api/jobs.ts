import { requireAuth, refreshTokens } from '../composables/useAuth'
import type { MatchesResponse, RunResponse, RunReport, JobStatus } from '../types/jobs'

const BASE = import.meta.env.DEV ? '' : 'https://adel-intelligence.com'

async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  let token = await requireAuth()

  const makeRequest = (t: string) =>
    fetch(url, {
      ...options,
      headers: {
        Authorization: `Bearer ${t}`,
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string> ?? {}),
      },
    })

  let res = await makeRequest(token)

  if (res.status === 401) {
    await refreshTokens()
    token = await requireAuth()
    res = await makeRequest(token)
  }

  return res
}

export async function fetchMatches(params: {
  tier?: string
  country?: string
  status?: string
  platform?: string
}): Promise<MatchesResponse> {
  const query = new URLSearchParams()
  if (params.tier)     query.set('tier',     params.tier)
  if (params.country)  query.set('country',  params.country)
  if (params.status)   query.set('status',   params.status)
  if (params.platform) query.set('platform', params.platform)

  const qs = query.toString()
  const res = await authFetch(`${BASE}/api/jobs/matches${qs ? `?${qs}` : ''}`)
  if (!res.ok) throw new Error(`Failed to fetch matches: HTTP ${res.status}`)
  return res.json() as Promise<MatchesResponse>
}

export async function triggerRun(): Promise<RunResponse> {
  const res = await authFetch(`${BASE}/api/jobs/run`)
  if (!res.ok) throw new Error(`Failed to trigger run: HTTP ${res.status}`)
  return res.json() as Promise<RunResponse>
}

export async function fetchReport(): Promise<RunReport> {
  const res = await authFetch(`${BASE}/api/jobs/report`)
  if (!res.ok) throw new Error(`Failed to fetch report: HTTP ${res.status}`)
  return res.json() as Promise<RunReport>
}

export async function updateMatchStatus(id: number, status: JobStatus): Promise<void> {
  const res = await authFetch(`${BASE}/api/jobs/matches/${id}/status`, {
    method: 'POST',
    body: JSON.stringify({ status }),
  })
  if (!res.ok) throw new Error(`Failed to update status: HTTP ${res.status}`)
}
