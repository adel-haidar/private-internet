/** Shared plan definitions used by LandingView and SubscribeView. */

export interface Plan {
  key: 'free' | 'pro' | 'max'
  name: string
  price: string
  period: string
  cta: string
  highlight: boolean
  features: string[]
}

/**
 * Maps a gated feature key OR a route path to a human label and the plan that
 * unlocks it. Used by SubscribeView to explain *why* the user landed there.
 * Accepts both `stories` and `/stories` (the route guard sends the path).
 */
export const FEATURE_LABELS: Record<string, { label: string; plan: 'pro' | 'max' }> = {
  aria:        { label: 'ARIA — AI music',              plan: 'pro' },
  signal:      { label: 'SIGNAL — AI video channel',   plan: 'pro' },
  stories:     { label: 'STORIES — AI films & series', plan: 'max' },
  pulse_media: { label: 'Images & video in your feed', plan: 'pro' },
}

export function resolveFeature(
  raw: string | null | undefined,
): { label: string; plan: 'pro' | 'max' } | null {
  if (!raw) return null
  const key = raw.replace(/^\//, '') // "/stories" -> "stories"
  return FEATURE_LABELS[key] ?? null
}

export const PLANS: Plan[] = [
  {
    key: 'free',
    name: 'Free',
    price: '€0',
    period: '',
    cta: 'Get started free',
    highlight: false,
    features: [
      'Health insights',
      'Job hunt agent',
      'Finance analysis',
      'Personal memory brain',
      'Text social feed (PULSE)',
    ],
  },
  {
    key: 'pro',
    name: 'Pro',
    price: '€19',
    period: '/mo',
    cta: 'Start Pro',
    highlight: true,
    features: [
      'Everything in Free',
      'AI music (ARIA)',
      'AI video channel (SIGNAL)',
      'Images & video in your feed',
    ],
  },
  {
    key: 'max',
    name: 'Max',
    price: '€39',
    period: '/mo',
    cta: 'Start Max',
    highlight: false,
    features: [
      'Everything in Pro',
      'AI short films & series (STORIES)',
    ],
  },
]
