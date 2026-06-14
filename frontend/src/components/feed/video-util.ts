/** Small helpers for SIGNAL video cards/player. */
import type { Video } from '../../composables/useContent'

/** Seconds → "m:ss" (empty when unknown). */
export function fmtSecs(secs: number | null | undefined): string {
  if (secs == null || secs <= 0) return ''
  return `${Math.floor(secs / 60)}:${String(Math.round(secs % 60)).padStart(2, '0')}`
}

/** True while the video is still rendering. */
export function isProcessing(v: Video): boolean {
  return v.status === 'processing' || v.status === 'pending'
}

/** True when a playable URL exists. */
export function isPlayable(v: Video): boolean {
  return v.status === 'ready' && !!v.video_url
}
