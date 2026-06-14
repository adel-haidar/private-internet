<script setup lang="ts">
/**
 * Playlist / album detail — art, meta, actions, and a track list where the
 * playing row gets an accent border + amber tint.
 * Fetches real playlist data from GET /api/aria/playlists/{id}.
 */
import { computed, ref, onMounted, watch } from 'vue'
import {
  useAria, arArtBackground, arArtStyle, AR_MOOD_COLOR, fetchPlaylist,
  type AriaPlaylist as AriaPlaylistType,
} from '../../composables/useAria'

const props = defineProps<{ playlistId: string }>()
const emit = defineEmits<{ (e: 'back'): void }>()

const { track, playing, playTrack, toggle, isLiked, toggleLike, setShuffle } = useAria()

const pl = ref<AriaPlaylistType | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    pl.value = await fetchPlaylist(props.playlistId)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.playlistId, load)

const tracks = computed(() => pl.value?.tracks ?? [])
const ids = computed(() => tracks.value.map((t) => t.id))

const totalLabel = computed(() => {
  if (!pl.value) return ''
  const secs = pl.value.total_duration
  const h = Math.floor(secs / 3600)
  const m = Math.round((secs % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
})
</script>

<template>
  <!-- loading -->
  <div v-if="loading" class="apd__loading">Loading playlist…</div>

  <!-- error -->
  <div v-else-if="error" class="apd__error">
    <p>{{ error }}</p>
    <button class="apd__back" @click="load()">Retry</button>
  </div>

  <div v-else-if="pl" class="apd">
    <button class="apd__back" @click="emit('back')">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M15 18l-6-6 6-6"/></svg>
      Back to Aria
    </button>

    <div
      class="apd__art"
      :style="pl.art_url
        ? { backgroundImage: `url(${pl.art_url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
        : arArtStyle(pl.name, pl.mood)"
    />
    <h1 class="apd__name">{{ pl.name }}</h1>
    <div class="apd__meta mono">{{ pl.track_count }} tracks · {{ totalLabel }}</div>

    <div class="apd__actions">
      <button class="apd__btn apd__btn--primary" @click="tracks.length && playTrack(tracks[0], ids)">Play</button>
      <button class="apd__btn" @click="setShuffle(true); tracks.length && playTrack(tracks[0], ids)">Shuffle</button>
    </div>

    <!-- track list -->
    <div v-if="tracks.length > 0" class="apd__list">
      <div
        v-for="(t, i) in tracks" :key="t.id"
        class="apd__rowwrap" :class="{ 'apd__rowwrap--on': track && track.id === t.id }"
      >
        <button class="apd__row" @click="track && track.id === t.id ? toggle() : playTrack(t, ids)">
          <span class="apd__num">
            <template v-if="track && track.id === t.id">
              <svg v-if="playing" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="color:var(--accent-primary)"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="color:var(--accent-primary)"><path d="M8 5v14l11-7z"/></svg>
            </template>
            <span v-else class="mono">{{ i + 1 }}</span>
          </span>
          <span class="apd__rart" :style="arArtBackground(t)" />
          <span class="apd__rtitle">{{ t.title }}</span>
          <span class="apd__rmood" :style="{ color: AR_MOOD_COLOR[t.mood] }">{{ t.mood }}</span>
          <span class="mono apd__rdur">{{ t.dur }}</span>
        </button>
        <button class="apd__like" :class="{ 'apd__like--on': isLiked(t.id) }" @click="toggleLike(t.id)" aria-label="Like">
          <svg width="16" height="16" viewBox="0 0 24 24" :fill="isLiked(t.id) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8"><path d="M20.8 5.6a5.5 5.5 0 0 0-7.8 0L12 6.6l-1-1a5.5 5.5 0 1 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>
        </button>
      </div>
    </div>
    <div v-else class="apd__empty">No tracks in this playlist yet.</div>
  </div>
</template>

<style scoped>
.apd__loading { font-family: var(--font-body); font-size: 14px; color: var(--text-tertiary); padding: 40px; text-align: center; }
.apd__error { font-family: var(--font-body); font-size: 14px; color: var(--text-secondary); padding: 24px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.apd { max-width: 560px; margin: 0 auto; }
.apd__back { display: inline-flex; align-items: center; gap: 6px; background: none; border: 0; color: var(--accent-primary); cursor: pointer; font-size: 14px; margin-bottom: 16px; }
.apd__art { width: 220px; height: 220px; margin: 0 auto; border-radius: 16px; display: block; }
.apd__name { text-align: center; font-family: var(--font-display); font-weight: 600; font-size: 22px; color: var(--text-primary); margin: 18px 0 6px; }
.apd__meta { text-align: center; font-size: 12px; color: var(--text-tertiary); }
.mono { font-family: var(--font-mono); }
.apd__actions { display: flex; justify-content: center; gap: 12px; margin: 20px 0 24px; }
.apd__btn { height: 40px; padding: 0 18px; border-radius: 8px; border: 1px solid var(--border-medium); background: transparent; color: var(--text-primary); cursor: pointer; font-size: 14px; }
.apd__btn--primary { background: var(--accent-primary); border-color: var(--accent-primary); color: #fff; }
.apd__rowwrap { display: flex; align-items: center; border-bottom: 0.5px solid var(--border-subtle); border-left: 3px solid transparent; }
.apd__rowwrap--on { border-left-color: var(--accent-primary); background: color-mix(in srgb, var(--brain-amber) 8%, transparent); }
.apd__row { flex: 1; display: flex; align-items: center; gap: 12px; padding: 10px; background: none; border: 0; cursor: pointer; text-align: left; min-width: 0; }
.apd__num { width: 24px; text-align: center; color: var(--text-tertiary); display: flex; justify-content: center; }
.apd__rart { width: 40px; height: 40px; border-radius: 6px; flex: 0 0 auto; display: block; }
.apd__rtitle { flex: 1; font-size: 15px; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.apd__rmood { font-size: 12px; flex: 0 0 auto; }
.apd__rdur { font-size: 11px; color: var(--text-tertiary); flex: 0 0 auto; }
.apd__like { background: none; border: 0; cursor: pointer; color: var(--text-secondary); padding: 8px; }
.apd__like--on { color: var(--brain-amber); }
.apd__empty { font-family: var(--font-serif); font-size: 14px; color: var(--text-tertiary); padding: 24px; text-align: center; }
</style>
