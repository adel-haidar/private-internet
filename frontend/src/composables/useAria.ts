/**
 * useAria — module-scoped singleton for ARIA continuous playback.
 *
 * Data is fetched from /api/aria (real backend).
 * Playback progress is simulated via a timer (real audio engine TBD).
 * State lives at module scope so music continues across navigation.
 */

import { ref, readonly, computed } from 'vue'
import { requireAuth } from './useAuth'
import { API_BASE } from '../config/env'

// ── Types ─────────────────────────────────────────────────────────────────────

export type ArMood = 'Calm' | 'Focus' | 'Energetic' | 'Melancholic' | 'Uplifting' | 'Tense'

/** Maps the lowercase mood strings from the API to the ArMood display type. */
const MOOD_MAP: Record<string, ArMood> = {
  calm: 'Calm',
  focus: 'Focus',
  energetic: 'Energetic',
  melancholic: 'Melancholic',
  uplifting: 'Uplifting',
  tense: 'Tense',
}

function normaliseMood(raw: string | undefined): ArMood {
  if (!raw) return 'Calm'
  return MOOD_MAP[raw.toLowerCase()] ?? 'Calm'
}

/** Raw shape from GET /api/aria/tracks/{id} and the library. */
interface TrackOut {
  id: string
  title: string
  mood: string            // lowercase from API
  genre?: string
  topic_category?: string
  duration_seconds?: number
  status: 'generating' | 'ready' | 'failed'
  audio_url?: string
  waveform_url?: string
  art_url?: string
  lyrics?: string         // newline-separated string
  bpm?: number
  musical_key?: string
  instruments: string[]
  brain_topic_ids: string[]
  is_liked: boolean
  created_at: string
  updated_at: string
}

/** Raw shape from GET /api/aria/playlists/{id} and the library. */
interface PlaylistOut {
  id: string
  title: string
  dominant_mood?: string  // lowercase
  art_url?: string
  track_count: number
  total_duration: number  // int secs
  is_auto_generated: boolean
  tracks?: TrackOut[]
}

/** A single line of a podcast transcript. */
export interface PodcastLine {
  host: 'A' | 'B'
  text: string
}

/** Normalised track shape used throughout the UI.
 * `kind` discriminates music tracks from podcasts so the single shared player,
 * mini-player and Now Playing overlay can drive both. */
export interface AriaTrack {
  id: string
  title: string
  mood: ArMood
  genre?: string
  dur: string             // formatted "M:SS"
  duration_seconds?: number
  topic?: string
  key?: string
  inst?: string
  lyrics?: readonly string[]  // split on \n
  status?: 'processing'  // undefined = ready
  audio_url?: string
  art_url?: string
  is_liked: boolean
  // Podcast-only fields (kind === 'podcast'); undefined for music tracks.
  kind?: 'track' | 'podcast'
  transcript?: readonly PodcastLine[]
  hostAName?: string
  hostBName?: string
}

/** Raw shape from GET /api/aria/podcasts (list). */
interface PodcastSummaryOut {
  id: string
  title: string
  description?: string
  topic_category?: string
  duration_seconds?: number
  status: 'generating' | 'ready' | 'failed'
  art_url?: string
  language_code: string
  is_liked: boolean
  created_at: string
}

/** Raw shape from GET /api/aria/podcasts/{id} (detail). */
interface PodcastDetailOut extends PodcastSummaryOut {
  audio_url?: string
  waveform_url?: string
  transcript: PodcastLine[]
  brain_topic_ids: string[]
  host_a_name: string
  host_b_name: string
}

/** Normalised podcast shape used by the library cards. */
export interface AriaPodcast {
  id: string
  title: string
  description?: string
  topic?: string
  dur: string             // "12 min"
  duration_seconds?: number
  art_url?: string
  status?: 'processing'   // undefined = ready
  is_liked: boolean
}

/** Normalised playlist shape. */
export interface AriaPlaylist {
  id: string
  name: string
  mood: ArMood
  art_url?: string
  track_count: number
  total_duration: number
  trackIds: string[]
  tracks?: AriaTrack[]
}

// ── Normalisation helpers ─────────────────────────────────────────────────────

function normTrack(t: TrackOut): AriaTrack {
  return {
    id: t.id,
    title: t.title,
    mood: normaliseMood(t.mood),
    genre: t.genre,
    dur: t.duration_seconds != null ? arFmt(t.duration_seconds) : '',
    duration_seconds: t.duration_seconds,
    topic: t.topic_category,
    key: t.musical_key,
    inst: t.instruments?.join(', ') || undefined,
    lyrics: t.lyrics ? t.lyrics.split('\n').filter(Boolean) : undefined,
    status: t.status === 'generating' ? 'processing' : undefined,
    audio_url: t.audio_url,
    art_url: t.art_url,
    is_liked: t.is_liked,
  }
}

function normPlaylist(p: PlaylistOut): AriaPlaylist {
  return {
    id: p.id,
    name: p.title,
    mood: normaliseMood(p.dominant_mood),
    art_url: p.art_url,
    track_count: p.track_count,
    total_duration: p.total_duration,
    trackIds: p.tracks?.map((t) => t.id) ?? [],
    tracks: p.tracks?.map(normTrack),
  }
}

function normPodcast(p: PodcastSummaryOut): AriaPodcast {
  return {
    id: p.id,
    title: p.title,
    description: p.description,
    topic: p.topic_category || undefined,
    dur: p.duration_seconds != null ? arMin(p.duration_seconds) : '',
    duration_seconds: p.duration_seconds,
    art_url: p.art_url,
    status: p.status === 'generating' ? 'processing' : undefined,
    is_liked: p.is_liked,
  }
}

/** Podcasts reuse the music player; convert a fetched detail into an AriaTrack.
 * Podcasts have no mood, so they borrow the 'Focus' palette for consistent
 * theming — the UI distinguishes them with a microphone icon, not colour. */
function podcastToTrack(d: PodcastDetailOut): AriaTrack {
  return {
    id: d.id,
    title: d.title,
    mood: 'Focus',
    dur: d.duration_seconds != null ? arFmt(d.duration_seconds) : '',
    duration_seconds: d.duration_seconds,
    topic: d.topic_category || undefined,
    audio_url: d.audio_url,
    art_url: d.art_url,
    is_liked: d.is_liked,
    kind: 'podcast',
    transcript: d.transcript ?? [],
    hostAName: d.host_a_name,
    hostBName: d.host_b_name,
  }
}

// ── Mood system ───────────────────────────────────────────────────────────────

export const AR_MOODS: ArMood[] = ['Calm', 'Focus', 'Energetic', 'Melancholic', 'Uplifting', 'Tense']

export const AR_MOOD_COLOR: Record<ArMood, string> = {
  Calm: '#6B8CAE',
  Focus: '#5B5BD6',
  Energetic: '#C0392B',
  Melancholic: '#7C3AED',
  Uplifting: '#2D7A4F',
  Tense: '#B45309',
}

// ── API base ─────────────────────────────────────────────────────────────────

const BASE = `${API_BASE}/api/aria`

async function arGet<T>(path: string): Promise<T> {
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

async function arPost<T>(path: string, body: unknown): Promise<T> {
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

// ── Library state (module-scoped) ─────────────────────────────────────────────

const _libTracks = ref<AriaTrack[]>([])
const _libPlaylists = ref<AriaPlaylist[]>([])
const _libPodcasts = ref<AriaPodcast[]>([])
const _libLoading = ref(false)
const _libError = ref<string | null>(null)
const _libLoaded = ref(false)
const _likedCount = ref(0)
const _totalTracks = ref(0)

/** Fetch and populate the library. */
async function loadLibrary(force = false): Promise<void> {
  if (_libLoaded.value && !force) return
  _libLoading.value = true
  _libError.value = null
  try {
    // Library (tracks + playlists) and podcasts load together; a podcast
    // failure must not blank the music library, so it degrades to [].
    const [data, podcasts] = await Promise.all([
      arGet<{
        tracks: TrackOut[]
        playlists: PlaylistOut[]
        liked_count: number
        total_tracks: number
      }>('/library'),
      arGet<PodcastSummaryOut[]>('/podcasts').catch(() => [] as PodcastSummaryOut[]),
    ])
    _libTracks.value = data.tracks.map(normTrack)
    _libPlaylists.value = data.playlists.map(normPlaylist)
    _libPodcasts.value = podcasts.map(normPodcast)
    _likedCount.value = data.liked_count
    _totalTracks.value = data.total_tracks
    // Sync liked state into the player liked set from API data (tracks + podcasts).
    const liked = new Set(data.tracks.filter((t) => t.is_liked).map((t) => t.id))
    podcasts.filter((p) => p.is_liked).forEach((p) => liked.add(p.id))
    _liked.value = liked
    _libLoaded.value = true
  } catch (e) {
    _libError.value = e instanceof Error ? e.message : String(e)
  } finally {
    _libLoading.value = false
  }
}

/** Fetch a single playlist with its tracks. */
export async function fetchPlaylist(id: string): Promise<AriaPlaylist> {
  const data = await arGet<PlaylistOut>(`/playlists/${id}`)
  return normPlaylist(data)
}

/** Fetch a single podcast's detail (audio_url + transcript) as a playable track. */
export async function fetchPodcast(id: string): Promise<AriaTrack> {
  const data = await arGet<PodcastDetailOut>(`/podcasts/${id}`)
  return podcastToTrack(data)
}

/** Search tracks. */
export async function searchAria(q: string): Promise<{ query: string; tracks: AriaTrack[] }> {
  const data = await arGet<{ query: string; tracks: TrackOut[] }>(`/search?q=${encodeURIComponent(q)}`)
  return { query: data.query, tracks: data.tracks.map(normTrack) }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

export function arFmt(t: number): string {
  const abs = Math.max(0, Math.round(t))
  return `${Math.floor(abs / 60)}:${String(abs % 60).padStart(2, '0')}`
}

/** Coarse "N min" label for podcasts (not the music "M:SS" format). */
export function arMin(secs: number): string {
  return `${Math.max(1, Math.round(secs / 60))} min`
}

/** Duration in seconds from the track's dur string or duration_seconds field. */
export function arSecs(t: AriaTrack): number {
  if (t.duration_seconds != null) return t.duration_seconds
  if (!t.dur) return 210
  const parts = t.dur.split(':').map(Number)
  return parts[0] * 60 + (parts[1] ?? 0)
}

function arHash(s: string): number {
  let h = 0
  s = s || 'x'
  for (let i = 0; i < s.length; i++) h = ((h * 31 + s.charCodeAt(i)) >>> 0)
  return h
}

const AR_ALT = ['#E8A444', '#5B5BD6', '#0D9488', '#BE185D', '#7C3AED', '#0891B2', '#2D7A4F']

export function arArtStyle(seed: string, mood: ArMood): Record<string, string> {
  const base = AR_MOOD_COLOR[mood] || '#5B5BD6'
  const alt = AR_ALT[arHash(seed) % AR_ALT.length]
  return {
    background: `radial-gradient(circle at 28% 26%, ${base}dd, transparent 60%), radial-gradient(circle at 78% 74%, ${alt}bb, transparent 56%), linear-gradient(140deg, ${base}55, #0c0c14 92%)`,
  }
}

/** Art style: use art_url when available, else the gradient. */
export function arArtBackground(track: AriaTrack): Record<string, string> {
  if (track.art_url) {
    return { backgroundImage: `url(${track.art_url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
  }
  return arArtStyle(track.title || track.id, track.mood)
}

export function arBars(id: string, n = 56): number[] {
  const h = arHash(id)
  const out: number[] = []
  for (let i = 0; i < n; i++) {
    const v = (Math.sin(i * 0.7 + h) + Math.sin(i * 0.23 + h * 0.5) + 2) / 4
    out.push(0.18 + v * 0.82)
  }
  return out
}

// ── Module-scoped player state ────────────────────────────────────────────────

const _track = ref<AriaTrack | null>(null)
const _playing = ref(false)
const _progress = ref(0)          // 0–100
const _liked = ref<Set<string>>(new Set())
const _queue = ref<string[]>([])  // upcoming track ids
const _nowOpen = ref(false)
const _shuffle = ref(false)
const _repeat = ref(false)
const _volume = ref(70)

// Play session tracking for POST /play-end
let _currentPlayId: string | null = null

// Real playback engine: a single shared HTMLAudioElement driven by the track's
// audio_url, with a simulated-timer fallback for tracks that have no audio URL
// (still generating) or non-browser contexts (SSR/tests).
let _audio: HTMLAudioElement | null = null
let _tickId: ReturnType<typeof setInterval> | null = null
let _engineActive = false

function _ensureAudio(): HTMLAudioElement | null {
  if (typeof window === 'undefined' || typeof Audio === 'undefined') return null
  if (_audio) return _audio
  _audio = new Audio()
  _audio.preload = 'metadata'
  _audio.addEventListener('timeupdate', () => {
    if (!_engineActive || !_audio) return
    const d = _audio.duration
    if (Number.isFinite(d) && d > 0) _progress.value = (_audio.currentTime / d) * 100
  })
  _audio.addEventListener('ended', () => {
    if (!_engineActive) return
    if (_repeat.value && _audio) { _audio.currentTime = 0; _audio.play().catch(() => {}) }
    else _next()
  })
  return _audio
}

function _startFallbackTick() {
  if (_tickId) clearInterval(_tickId)
  _tickId = setInterval(() => {
    if (!_playing.value || !_track.value) return
    const total = arSecs(_track.value)
    _progress.value = _progress.value + (100 / total) * 0.5 // 0.5s steps
    if (_progress.value >= 100) {
      if (_repeat.value) {
        _progress.value = 0
      } else {
        setTimeout(() => _next(), 0)
        _progress.value = 100
      }
    }
  }, 500)
}

function _stopFallbackTick() {
  if (_tickId) { clearInterval(_tickId); _tickId = null }
}

/** Load the current `_track` into the engine and start it from 0. */
function _engage() {
  const t = _track.value
  if (!t) return
  const el = _ensureAudio()
  if (el && t.audio_url) {
    _engineActive = true
    _stopFallbackTick()
    if (el.src !== t.audio_url) el.src = t.audio_url
    el.volume = _volume.value / 100
    el.currentTime = 0
    el.play().catch(() => {})
  } else {
    _engineActive = false
    if (el) { try { el.pause() } catch { /* ignore */ } }
    _progress.value = 0
    _startFallbackTick()
  }
}

/** Resume the current track at its current position. */
function _resume() {
  if (_engineActive && _audio) _audio.play().catch(() => {})
  else _startFallbackTick()
}

/** Pause without unloading. */
function _pauseEngine() {
  _stopFallbackTick()
  if (_engineActive && _audio) { try { _audio.pause() } catch { /* ignore */ } }
}

async function _apiPlay(trackId: string): Promise<string | null> {
  try {
    const data = await arPost<{ play_id: string; track: TrackOut }>('/play', { track_id: trackId })
    return data.play_id
  } catch {
    return null
  }
}

async function _apiPlayEnd(playId: string, durationSecs: number): Promise<void> {
  try {
    await arPost('/play-end', { play_id: playId, play_duration_seconds: durationSecs })
  } catch { /* best-effort */ }
}

function _next() {
  if (_queue.value.length) {
    const [head, ...rest] = _queue.value
    const t = _libTracks.value.find((x) => x.id === head)
    if (t) {
      _track.value = t
      _progress.value = 0
      _playing.value = true
      _queue.value = rest
      _engage()
      _apiPlay(t.id).then((id) => { _currentPlayId = id })
    }
  } else {
    const ready = _libTracks.value.filter((x) => !x.status)
    const i = ready.findIndex((x) => _track.value && x.id === _track.value.id)
    const t = ready[(i + 1) % ready.length]
    if (t) {
      _track.value = t
      _progress.value = 0
      _playing.value = true
      _engage()
      _apiPlay(t.id).then((id) => { _currentPlayId = id })
    }
  }
}

// ── Public composable ─────────────────────────────────────────────────────────

export function useAria() {
  const isLiked = (id: string) => _liked.value.has(id)

  const remaining = computed(() => {
    if (!_track.value) return 0
    const total = arSecs(_track.value)
    return total * (1 - _progress.value / 100)
  })

  function playTrack(t: AriaTrack, queueIds?: string[]) {
    if (t.status === 'processing') return
    // End previous session
    if (_currentPlayId && _track.value) {
      const elapsed = arSecs(_track.value) * (_progress.value / 100)
      _apiPlayEnd(_currentPlayId, elapsed)
    }
    _track.value = t
    _progress.value = 0
    _playing.value = true
    if (queueIds) _queue.value = queueIds.filter((id) => id !== t.id)
    _apiPlay(t.id).then((id) => { _currentPlayId = id })
    _engage()
  }

  /** Play a podcast through the shared player. Fetches detail (audio_url +
   * transcript) first; no music queue is set and no track play-session API is
   * called (podcasts aren't rows in aria_play_history). */
  async function playPodcast(p: AriaPodcast) {
    if (p.status === 'processing') return
    // End any in-flight music play session before switching.
    if (_currentPlayId && _track.value) {
      const elapsed = arSecs(_track.value) * (_progress.value / 100)
      _apiPlayEnd(_currentPlayId, elapsed)
      _currentPlayId = null
    }
    let t: AriaTrack
    try {
      t = await fetchPodcast(p.id)
    } catch {
      return
    }
    _track.value = t
    _progress.value = 0
    _playing.value = true
    _queue.value = []
    _engage()
  }

  function toggle() {
    if (!_track.value) return
    _playing.value = !_playing.value
    if (_playing.value) {
      _resume()
    } else {
      _pauseEngine()
    }
  }

  function next() { _next() }

  function prev() {
    _progress.value = 0
    if (_engineActive && _audio) _audio.currentTime = 0
  }

  function seek(pct: number) {
    const p = Math.max(0, Math.min(100, pct))
    _progress.value = p
    if (_engineActive && _audio && Number.isFinite(_audio.duration)) {
      _audio.currentTime = (p / 100) * _audio.duration
    }
  }

  function toggleLike(id: string) {
    const s = new Set(_liked.value)
    const nowLiked = !s.has(id)
    nowLiked ? s.add(id) : s.delete(id)
    _liked.value = s
    // Podcasts and tracks have distinct like endpoints/payloads — route by kind.
    const isPodcast =
      _libPodcasts.value.some((p) => p.id === id) ||
      (_track.value?.kind === 'podcast' && _track.value.id === id)
    const req = isPodcast
      ? arPost(`/podcasts/${id}/like`, { liked: nowLiked })
      : arPost('/like', { track_id: id, liked: nowLiked })
    // Fire-and-forget; revert on failure.
    req.catch(() => {
      const r = new Set(_liked.value)
      nowLiked ? r.delete(id) : r.add(id)
      _liked.value = r
    })
  }

  function enqueue(id: string) {
    if (!_queue.value.includes(id)) _queue.value = [..._queue.value, id]
  }

  function dequeue(idx: number) {
    _queue.value = _queue.value.filter((_, i) => i !== idx)
  }

  function openNow() { _nowOpen.value = true }
  function closeNow() { _nowOpen.value = false }

  function setShuffle(v: boolean) { _shuffle.value = v }
  function setRepeat(v: boolean) { _repeat.value = v }
  function setVolume(v: number) {
    _volume.value = v
    if (_audio) _audio.volume = v / 100
  }
  function setQueue(ids: string[]) { _queue.value = ids }

  /** Get a track from the library by id (for queue display). */
  function getTrack(id: string): AriaTrack | undefined {
    return _libTracks.value.find((t) => t.id === id)
  }

  return {
    // state (readonly refs)
    track: readonly(_track),
    playing: readonly(_playing),
    progress: readonly(_progress),
    liked: readonly(_liked),
    queue: readonly(_queue),
    nowOpen: readonly(_nowOpen),
    shuffle: readonly(_shuffle),
    repeat: readonly(_repeat),
    volume: readonly(_volume),
    remaining,
    // library state
    libTracks: readonly(_libTracks),
    libPlaylists: readonly(_libPlaylists),
    libPodcasts: readonly(_libPodcasts),
    libLoading: readonly(_libLoading),
    libError: readonly(_libError),
    libLoaded: readonly(_libLoaded),
    likedCount: readonly(_likedCount),
    totalTracks: readonly(_totalTracks),
    // methods
    isLiked,
    playTrack,
    playPodcast,
    toggle,
    next,
    prev,
    seek,
    toggleLike,
    enqueue,
    dequeue,
    openNow,
    closeNow,
    setShuffle,
    setRepeat,
    setVolume,
    setQueue,
    getTrack,
    loadLibrary,
  }
}
