/**
 * useStories — module-scoped singleton for STORIES navigation + API state.
 *
 * Data is fetched from /api/stories (real backend).
 * All stub arrays have been replaced with async fetchers.
 */

import { ref, readonly } from 'vue'
import { requireAuth } from './useAuth'
import { API_BASE } from '../config/env'

// ── Types ────────────────────────────────────────────────────────────────────

/** Matches the backend EpisodeSummary shape. */
export interface StoryEpisode {
  id: string
  series_id: string
  season_number: number
  episode_number: number
  title: string
  premise?: string
  video_url?: string
  thumbnail_url?: string
  duration_seconds?: number
  status: 'generating' | 'ready' | 'failed'
  // client-side watch progress (injected from /continue_watching)
  position_seconds?: number
  completed?: boolean
}

/** Matches FilmSummary / SeriesSummary + extras from the detail endpoints. */
export interface StoryItem {
  id: string
  kind: 'film' | 'series'
  title: string
  premise?: string
  category?: string
  thumbnail_url?: string
  poster_url?: string
  duration_seconds?: number
  status: 'generating' | 'ready' | 'failed'
  created_at?: string
  updated_at?: string
  // Film detail extras
  video_url?: string
  watch_progress?: { position_seconds: number; duration_seconds: number; completed: boolean } | null
  related?: readonly StoryItem[]
  liked?: boolean
  // Series detail extras
  episode_count?: number
  episodes?: readonly StoryEpisode[]
  user_id?: string
}

export interface ContinueItem {
  content_type: 'film' | 'episode'
  content_id: string
  title: string
  thumbnail_url?: string
  position_seconds: number
  duration_seconds: number
  completed: boolean
  last_watched_at: string
  // resolved from library (joined client-side)
  item?: StoryItem
  ep_number?: number
}

export interface StoriesCategory {
  category: string
  film_count: number
  series_count: number
}

export type StoriesView =
  | { name: 'library' }
  | { name: 'film'; id: string }
  | { name: 'series'; id: string }
  | { name: 'category'; cat: string }
  | { name: 'search' }

export interface WatchState {
  item: StoryItem
  ep?: number
}

// ── API base ─────────────────────────────────────────────────────────────────

const BASE = `${API_BASE}/api/stories`

async function stGet<T>(path: string): Promise<T> {
  const token = await requireAuth()
  const res = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

async function stPost<T>(path: string, body: unknown): Promise<T> {
  const token = await requireAuth()
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

// ── Library state (module-scoped, shared across all composable calls) ─────────

const _films = ref<StoryItem[]>([])
const _series = ref<StoryItem[]>([])
const _categories = ref<StoriesCategory[]>([])
const _continueWatching = ref<ContinueItem[]>([])
const _libraryLoading = ref(false)
const _libraryError = ref<string | null>(null)
const _libraryLoaded = ref(false)

/** Fetch and populate the library once. */
async function loadLibrary(force = false): Promise<void> {
  if (_libraryLoaded.value && !force) return
  _libraryLoading.value = true
  _libraryError.value = null
  try {
    const data = await stGet<{
      films: StoryItem[]
      series: StoryItem[]
      categories: StoriesCategory[]
      continue_watching: ContinueItem[]
    }>('/')
    _films.value = data.films.map((f) => ({ ...f, kind: 'film' as const }))
    _series.value = data.series.map((s) => ({ ...s, kind: 'series' as const }))
    _categories.value = data.categories
    _continueWatching.value = data.continue_watching
    _libraryLoaded.value = true
  } catch (e) {
    _libraryError.value = e instanceof Error ? e.message : String(e)
  } finally {
    _libraryLoading.value = false
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Format seconds as M:SS */
export function stFmt(t: number): string {
  const abs = Math.max(0, Math.round(t))
  return `${Math.floor(abs / 60)}:${String(abs % 60).padStart(2, '0')}`
}

/** Format seconds as human label (e.g. "24m" or "1h 4m"). */
export function stDurLabel(secs?: number): string {
  if (!secs) return ''
  const h = Math.floor(secs / 3600)
  const m = Math.round((secs % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

/** Watch-progress percentage 0-100. */
export function stProgressPct(wp?: { position_seconds: number; duration_seconds: number } | null): number | null {
  if (!wp || !wp.duration_seconds) return null
  return Math.min(100, Math.round((wp.position_seconds / wp.duration_seconds) * 100))
}

/** Remaining time label from a watch_progress object. */
export function stLeftLabel(wp?: { position_seconds: number; duration_seconds: number } | null): string {
  if (!wp || !wp.duration_seconds) return ''
  const left = Math.max(0, wp.duration_seconds - wp.position_seconds)
  const m = Math.round(left / 60)
  return m > 0 ? `${m}m left` : ''
}

/** Deterministic gradient poster (fallback when no thumbnail_url). */
const ST_SEED = ['#4F46E5', '#0891B2', '#0D9488', '#B45309', '#7C3AED', '#BE185D']

function stHash(s: string): number {
  let h = 0
  for (let i = 0; i < (s || 'x').length; i++) h = ((h * 31 + s.charCodeAt(i)) >>> 0)
  return h
}

function stColor(s: string): string {
  return ST_SEED[stHash(s || 'x') % ST_SEED.length]
}

export function stPosterStyle(seed: string): Record<string, string> {
  const c = stColor(seed)
  return {
    background: `radial-gradient(120% 80% at 70% 12%, ${c}66, transparent 55%), linear-gradient(160deg, ${c}59, #0c0c14 92%)`,
  }
}

// ── API helpers (exported for components) ─────────────────────────────────────

/** Load a single film detail (includes video_url, watch_progress, related, liked). */
export async function fetchFilm(id: string): Promise<StoryItem> {
  const data = await stGet<StoryItem & { kind?: 'film' }>(`/films/${id}`)
  return { ...data, kind: 'film' }
}

/** Load a single series detail (includes episode_count, liked). */
export async function fetchSeries(id: string): Promise<StoryItem> {
  const data = await stGet<StoryItem & { kind?: 'series' }>(`/series/${id}`)
  return { ...data, kind: 'series' }
}

/** Load episodes for a series. */
export async function fetchEpisodes(seriesId: string): Promise<StoryEpisode[]> {
  return stGet<StoryEpisode[]>(`/series/${seriesId}/episodes`)
}

/** Search films + series. */
export async function searchStories(q: string): Promise<{ films: StoryItem[]; series: StoryItem[] }> {
  const data = await stGet<{ films: StoryItem[]; series: StoryItem[] }>(`/search?q=${encodeURIComponent(q)}`)
  return {
    films: data.films.map((f) => ({ ...f, kind: 'film' as const })),
    series: data.series.map((s) => ({ ...s, kind: 'series' as const })),
  }
}

/** POST /progress — track watch position. */
export async function postProgress(payload: {
  content_type: 'film' | 'episode'
  content_id: string
  position_seconds: number
  duration_seconds?: number
}): Promise<void> {
  await stPost('/progress', payload)
}

/** POST /like — toggle like. */
export async function postLike(payload: {
  content_type: 'film' | 'series' | 'episode'
  content_id: string
  liked: boolean
}): Promise<void> {
  await stPost('/like', payload)
}

// ── Module-scoped navigation state ───────────────────────────────────────────

const _view = ref<StoriesView>({ name: 'library' })
const _watch = ref<WatchState | null>(null)

export function useStories() {
  function navigate(v: StoriesView) {
    _view.value = v
    window.scrollTo(0, 0)
  }

  function play(item: StoryItem, ep?: number) {
    _watch.value = { item, ep }
  }

  function stopWatch() {
    _watch.value = null
  }

  return {
    // navigation state
    view: readonly(_view),
    watch: readonly(_watch),
    navigate,
    play,
    stopWatch,
    // library state
    films: readonly(_films),
    series: readonly(_series),
    categories: readonly(_categories),
    continueWatching: readonly(_continueWatching),
    libraryLoading: readonly(_libraryLoading),
    libraryError: readonly(_libraryError),
    libraryLoaded: readonly(_libraryLoaded),
    // loader
    loadLibrary,
  }
}
