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
