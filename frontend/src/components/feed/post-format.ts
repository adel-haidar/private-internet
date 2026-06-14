/** Editorial derivations for PULSE posts — the backend has no topic name, link,
 * or reading-time fields, so we derive them locally (matching the mobile app). */
import type { Post } from '../../composables/useContent'

const URL_RE = /https?:\/\/[^\s)]+/i

export function firstUrl(body: string): string | null {
  return body.match(URL_RE)?.[0] ?? null
}

export function linkHost(url: string): string {
  try {
    return new URL(url).host.replace(/^www\./, '')
  } catch {
    return 'source'
  }
}

/** Headline = first sentence of the body, link-stripped, ≤72 chars. */
export function headline(body: string): string {
  const first = body.trim().split(/(?<=[.!?])\s/)[0].replace(URL_RE, '').trim()
  return first.length <= 72 ? first : first.slice(0, 69).trimEnd() + '…'
}

/** Reading time in minutes (~200 wpm, min 1). */
export function readMinutes(body: string): number {
  const words = body.trim().split(/\s+/).length
  return Math.max(1, Math.min(99, Math.ceil(words / 200)))
}

export type PostFormat = 'A' | 'B' | 'C'

/** A = image, C = external source, B = text-only. */
export function postFormat(p: Post): PostFormat {
  if (firstUrl(p.body)) return 'C'
  if (p.image_url) return 'A'
  return 'B'
}

/** Coarse relative age from an ISO timestamp. */
export function age(iso: string): string {
  const h = Math.floor((Date.now() - new Date(iso).getTime()) / 3.6e6)
  if (h < 1) return 'just now'
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

/** Format-B background tint by tone. */
export function toneTint(tone: Post['tone']): string {
  switch (tone) {
    case 'satirical': return 'color-mix(in srgb, var(--brain-amber-surface) 70%, var(--background-surface))'
    case 'critical': return 'color-mix(in srgb, var(--danger) 5%, var(--background-surface))'
    case 'supportive': return 'color-mix(in srgb, var(--success) 5%, var(--background-surface))'
    case 'informative': return 'color-mix(in srgb, var(--accent-surface) 60%, var(--background-surface))'
    default: return 'var(--background-surface)'
  }
}
