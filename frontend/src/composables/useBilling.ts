import { ref } from 'vue'
import { requireAuth } from './useAuth'
import { API_BASE } from '../config/env'

export interface BillingStatus {
  billing_enabled: boolean
  entitled: boolean
  subscription_status: string
  trial_days: number
  price_configured: boolean
  current_period_end: string | null
  plan: string
  plan_rank: number
  plan_ranks: Record<string, number>
  feature_min_plan: Record<string, string>
}

// Module-level cache so the router guard doesn't refetch on every navigation.
const status = ref<BillingStatus | null>(null)

async function fetchStatus(force = false): Promise<BillingStatus | null> {
  if (status.value && !force) return status.value
  try {
    const token = await requireAuth()
    const res = await fetch(`${API_BASE}/api/billing/status`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) return null
    status.value = (await res.json()) as BillingStatus
    return status.value
  } catch {
    return null
  }
}

/**
 * Returns true if the user has access to the given feature key.
 * When billing is disabled (current prod state) always returns true.
 * Features absent from feature_min_plan are free → true.
 */
function hasFeature(feature: string): boolean {
  const s = status.value
  if (!s) return true
  if (!s.billing_enabled) return true
  const minPlan = s.feature_min_plan[feature]
  if (!minPlan) return true // not gated
  const required = s.plan_ranks[minPlan] ?? 0
  return s.plan_rank >= required
}

/**
 * Returns true if the user meets the required plan level.
 * When billing is disabled always returns true.
 */
function meetsPlan(required: 'pro' | 'max'): boolean {
  const s = status.value
  if (!s) return true
  if (!s.billing_enabled) return true
  const requiredRank = s.plan_ranks[required] ?? 0
  return s.plan_rank >= requiredRank
}

async function startCheckout(plan: 'pro' | 'max'): Promise<void> {
  const token = await requireAuth()
  const res = await fetch(`${API_BASE}/api/billing/checkout`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ plan }),
  })
  const data = await res.json().catch(() => ({}))
  if (res.ok && data.url) {
    window.location.href = data.url as string
    return
  }
  throw new Error(data.error || 'Could not start checkout. Please try again.')
}

async function openPortal(): Promise<void> {
  const token = await requireAuth()
  const res = await fetch(`${API_BASE}/api/billing/portal`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  const data = await res.json().catch(() => ({}))
  if (res.ok && data.url) {
    window.location.href = data.url as string
    return
  }
  throw new Error(data.error || 'Could not open the billing portal.')
}

function clearBillingStatus(): void {
  status.value = null
}

export function useBilling() {
  return { status, fetchStatus, startCheckout, openPortal, clearBillingStatus, hasFeature, meetsPlan }
}

export { fetchStatus, clearBillingStatus, hasFeature, meetsPlan }
