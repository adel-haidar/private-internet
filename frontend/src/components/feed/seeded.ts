/**
 * Seeded creator identity for the editorial PULSE/SIGNAL surfaces — a stable
 * colour per creator name (avatar fill + thumbnail tint) and initials.
 * Mirrors the mobile redesign's seeded palette.
 */

const PALETTE = ['#4F46E5', '#0891B2', '#0D9488', '#B45309', '#7C3AED', '#BE185D']

function hash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return h
}

/** Consistent colour for a creator name. */
export function seededColor(name: string): string {
  return PALETTE[hash(name || '?') % PALETTE.length]
}

/** Up to two uppercase initials. */
export function initials(name: string): string {
  const parts = (name || '').trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0][0].toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

/** A subtle tinted gradient backdrop derived from the seed (over raised bg). */
export function seededThumb(seed: string): Record<string, string> {
  const c = seededColor(seed)
  return {
    background: `radial-gradient(circle at 72% 24%, ${c}3d, transparent 58%), linear-gradient(145deg, ${c}33, var(--background-raised) 72%)`,
  }
}

/** A hero background: seeded radial + linear wash (used when no real image). */
export function seededHero(seed: string): Record<string, string> {
  const c = seededColor(seed)
  return {
    background: `radial-gradient(circle at 28% 22%, ${c}66, transparent 62%), linear-gradient(142deg, ${c}40, var(--background-raised))`,
  }
}
