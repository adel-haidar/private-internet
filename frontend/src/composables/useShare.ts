/**
 * Global sharing composable.
 *
 * `createShare()` mints a public share token on the backend (POST /api/share),
 * returning a CloudFront-unfurlable URL anyone can open. The platform helpers
 * build per-platform "share intent" links (no per-platform account needed);
 * `nativeShare()` uses the OS share sheet on mobile when available.
 *
 * Sensitive sections (Health/Finance) pass `highlight` (headline/caption) instead
 * of a `refId` — the backend renders a privacy-preserving card image, never raw data.
 */
import { requireAuth, refreshTokens, hasRefreshToken } from './useAuth'
import { API_BASE } from '../config/env'

export type ShareKind =
  | 'pulse_post'
  | 'signal_video'
  | 'stories_film'
  | 'stories_episode'
  | 'aria_track'
  | 'aria_podcast'
  | 'health_card'
  | 'finance_card'

export interface ShareHighlight {
  headline: string
  caption?: string
  theme?: string
}

export interface CreateShareInput {
  kind: ShareKind
  refId?: string
  highlight?: ShareHighlight
  /** Suggested text shown alongside the link on platforms that support it. */
  text?: string
}

export interface ShareResult {
  token: string
  shareUrl: string
  /** Text to prefill on platforms that accept it (falls back to the title). */
  text: string
}

export interface ShareTarget {
  id: string
  label: string
  /** Brand colour for the dot in the menu. */
  color: string
  /** Web share-intent URL, or null for "copy + open app" platforms. */
  href: string | null
  /** Platforms with no web intent (Instagram/YouTube/Signal) → copy & open app. */
  copyOnly?: boolean
}

async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  let token = await requireAuth()
  const make = (t: string) =>
    fetch(url, {
      ...options,
      headers: {
        Authorization: `Bearer ${t}`,
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string> ?? {}),
      },
    })
  let res = await make(token)
  if (res.status === 401 && hasRefreshToken()) {
    await refreshTokens()
    token = await requireAuth()
    res = await make(token)
  }
  return res
}

/** Mint a public share link for an owned item (or a highlight card). */
export async function createShare(input: CreateShareInput): Promise<ShareResult> {
  const res = await authFetch(`${API_BASE}/api/share`, {
    method: 'POST',
    body: JSON.stringify({
      kind: input.kind,
      ref_id: input.refId ?? null,
      highlight: input.highlight ?? null,
    }),
  })
  if (!res.ok) {
    throw new Error(`Share failed (${res.status})`)
  }
  const data = await res.json()
  const title = data?.snapshot?.title ?? 'Check this out'
  return {
    token: data.token,
    shareUrl: data.share_url,
    text: input.text ?? title,
  }
}

/** True when the OS native share sheet is available (mobile/PWA). */
export function canNativeShare(): boolean {
  return typeof navigator !== 'undefined' && typeof navigator.share === 'function'
}

export async function nativeShare(result: ShareResult): Promise<boolean> {
  if (!canNativeShare()) return false
  try {
    await navigator.share({ title: result.text, text: result.text, url: result.shareUrl })
    return true
  } catch {
    // User cancelled or share rejected — fall back to the menu.
    return false
  }
}

/**
 * Build the per-platform target list for the share menu.
 * Intent URLs open a prefilled compose window; copy-only platforms have no web
 * intent so we copy the link and tell the user to paste it in the app.
 */
export function shareTargets(result: ShareResult): ShareTarget[] {
  const url = encodeURIComponent(result.shareUrl)
  const text = encodeURIComponent(result.text)
  const textUrl = encodeURIComponent(`${result.text} ${result.shareUrl}`)
  return [
    { id: 'x',        label: 'X',         color: '#000000',
      href: `https://twitter.com/intent/tweet?url=${url}&text=${text}` },
    { id: 'whatsapp', label: 'WhatsApp',  color: '#25d366',
      href: `https://wa.me/?text=${textUrl}` },
    { id: 'threads',  label: 'Threads',   color: '#000000',
      href: `https://www.threads.net/intent/post?text=${textUrl}` },
    { id: 'telegram', label: 'Telegram',  color: '#229ed9',
      href: `https://t.me/share/url?url=${url}&text=${text}` },
    { id: 'facebook', label: 'Facebook',  color: '#1877f2',
      href: `https://www.facebook.com/sharer/sharer.php?u=${url}` },
    { id: 'reddit',   label: 'Reddit',    color: '#ff4500',
      href: `https://www.reddit.com/submit?url=${url}&title=${text}` },
    { id: 'bluesky',  label: 'Bluesky',   color: '#0085ff',
      href: `https://bsky.app/intent/compose?text=${textUrl}` },
    { id: 'email',    label: 'Email',     color: '#6b7280',
      href: `mailto:?subject=${text}&body=${textUrl}` },
    { id: 'instagram', label: 'Instagram', color: '#e1306c', href: null, copyOnly: true },
    { id: 'youtube',   label: 'YouTube',   color: '#ff0000', href: null, copyOnly: true },
    { id: 'signal',    label: 'Signal',    color: '#3a76f0', href: null, copyOnly: true },
  ]
}

export async function copyLink(result: ShareResult): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(result.shareUrl)
    return true
  } catch {
    return false
  }
}
