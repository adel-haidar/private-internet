<script setup lang="ts">
/**
 * ARIA library — mood filter, now-playing hero, playlists, new tracks, the
 * signature "From your brain" section, and by-mood rows.
 * Data comes from the real /api/aria/library endpoint.
 */
import { ref, computed, onMounted } from 'vue'
import {
  useAria, arArtBackground, arArtStyle, AR_MOODS, AR_MOOD_COLOR,
  type ArMood, type AriaTrack,
} from '../../composables/useAria'

const emit = defineEmits<{ (e: 'open-playlist', id: string): void }>()
const {
  track, playing, toggle, playTrack, openNow,
  libTracks, libPlaylists, libLoading, libError, loadLibrary,
} = useAria()

onMounted(() => loadLibrary())

const mood = ref<ArMood | null>(null)

const readyIds = computed(() => libTracks.value.filter((t) => !t.status).map((t) => t.id))

const tracks = computed(() =>
  mood.value ? libTracks.value.filter((t) => t.mood === mood.value) : libTracks.value,
)

const moodsPresent = computed(() =>
  AR_MOODS.filter((m) => libTracks.value.some((t) => t.mood === m && !t.status)),
)

function play(t: AriaTrack) {
  if (t.status) return
  playTrack(t, readyIds.value)
}
</script>

<template>
  <div class="al">
    <div class="al__masthead">ARIA</div>

    <!-- loading -->
    <div v-if="libLoading" class="al__loading">Loading your music…</div>

    <!-- error -->
    <div v-else-if="libError" class="al__error">
      <p>Could not load library: {{ libError }}</p>
      <button class="al__retry" @click="loadLibrary(true)">Retry</button>
    </div>

    <template v-else>
      <!-- mood filter -->
      <div class="al__moods">
        <button class="al__mood" :class="{ 'al__mood--on': mood === null }" @click="mood = null">All</button>
        <button
          v-for="m in moodsPresent" :key="m" class="al__mood"
          :style="mood === m ? { background: AR_MOOD_COLOR[m], color: '#fff', borderColor: AR_MOOD_COLOR[m] } : { color: AR_MOOD_COLOR[m], borderColor: AR_MOOD_COLOR[m] }"
          @click="mood = m"
        >{{ m }}</button>
      </div>

      <!-- now playing hero -->
      <div v-if="track" class="al__now" :style="{ background: 'color-mix(in srgb, ' + AR_MOOD_COLOR[track.mood] + ' 10%, var(--background-surface))' }" @click="openNow">
        <span class="al__now-art" :style="arArtBackground(track)" />
        <div class="al__now-meta">
          <div class="al__now-eyebrow mono">Now playing</div>
          <div class="al__now-title">{{ track.title }}</div>
          <div class="al__now-mood" :style="{ color: AR_MOOD_COLOR[track.mood] }">{{ track.mood }}</div>
        </div>
        <button class="al__now-play" aria-label="Play/pause" @click.stop="toggle">
          <svg v-if="playing" width="26" height="26" viewBox="0 0 24 24" fill="currentColor"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg>
          <svg v-else width="26" height="26" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
        </button>
      </div>

      <!-- playlists -->
      <template v-if="libPlaylists.length > 0">
        <h3 class="al__h">Your playlists</h3>
        <div class="al__row">
          <button v-for="pl in libPlaylists" :key="pl.id" class="al__card" @click="emit('open-playlist', pl.id)">
            <span class="al__sq" :style="pl.art_url ? { backgroundImage: `url(${pl.art_url})`, backgroundSize: 'cover', backgroundPosition: 'center' } : arArtStyle(pl.name, pl.mood)">
              <span class="al__count mono">{{ pl.track_count }} tracks</span>
            </span>
            <span class="al__name">{{ pl.name }}</span>
            <span class="al__sub" :style="{ color: AR_MOOD_COLOR[pl.mood] }">{{ pl.mood }}</span>
          </button>
        </div>
      </template>

      <!-- new tracks -->
      <template v-if="tracks.length > 0">
        <h3 class="al__h">New tracks</h3>
        <div class="al__row">
          <button v-for="t in tracks" :key="t.id" class="al__card" @click="play(t)">
            <span class="al__sq" :style="arArtBackground(t)">
              <span v-if="t.status" class="al__gen">Generating…</span>
              <span v-else class="al__dur mono">{{ t.dur }}</span>
            </span>
            <span class="al__name">{{ t.status ? 'New track' : t.title }}</span>
            <span class="al__sub" :style="{ color: AR_MOOD_COLOR[t.mood] }">{{ t.mood }}</span>
          </button>
        </div>
      </template>

      <!-- from your brain -->
      <template v-if="tracks.filter((x) => !x.status).length > 0">
        <h3 class="al__h">From your brain</h3>
        <button v-for="t in tracks.filter((x) => !x.status).slice(0, 4)" :key="t.id" class="al__brain" @click="play(t)">
          <span class="al__brain-art" :style="arArtBackground(t)" />
          <span class="al__brain-meta">
            <span class="al__brain-title">{{ t.title }}</span>
            <span v-if="t.topic" class="al__brain-from">From: {{ t.topic }}</span>
          </span>
          <span class="mono al__brain-dur">{{ t.dur }}</span>
        </button>
      </template>

      <!-- by mood -->
      <template v-for="m in moodsPresent" :key="m">
        <h3 class="al__h">{{ m }}</h3>
        <div class="al__row">
          <button v-for="t in libTracks.filter((x) => x.mood === m && !x.status)" :key="t.id" class="al__card" @click="play(t)">
            <span class="al__sq" :style="arArtBackground(t)"><span class="al__dur mono">{{ t.dur }}</span></span>
            <span class="al__name">{{ t.title }}</span>
            <span class="al__sub" :style="{ color: AR_MOOD_COLOR[t.mood] }">{{ t.mood }}</span>
          </button>
        </div>
      </template>

      <!-- empty state -->
      <div v-if="libTracks.length === 0" class="al__empty">
        <p class="al__empty-title">No tracks yet</p>
        <p style="font-family: var(--font-serif); font-size: 14px; color: var(--text-secondary); margin-top: 8px">
          ARIA will generate music as your brain grows.
        </p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.al { max-width: var(--content-dashboard); margin: 0 auto; }
.al__masthead { font-family: var(--font-display); font-weight: 600; font-size: 15px; letter-spacing: 0.16em; margin-bottom: 16px; }
.al__loading { font-family: var(--font-body); font-size: 14px; color: var(--text-tertiary); padding: 40px 0; text-align: center; }
.al__error { font-family: var(--font-body); font-size: 14px; color: var(--text-secondary); padding: 24px; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); text-align: center; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.al__retry { height: 34px; padding: 0 16px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); background: transparent; color: var(--text-secondary); cursor: pointer; font-size: 13px; }
.al__retry:hover { border-color: var(--border-medium); color: var(--text-primary); }
.al__moods { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; margin-bottom: 20px; }
.al__mood { flex: 0 0 auto; height: 32px; padding: 0 14px; border-radius: 999px; border: 1px solid var(--accent-primary); color: var(--accent-primary); background: transparent; cursor: pointer; font-family: var(--font-display); font-weight: 500; font-size: 13px; }
.al__mood--on { background: var(--accent-primary); color: #fff; }
.al__now { display: flex; align-items: center; gap: 14px; padding: 12px; border-radius: 12px; border: 1px solid var(--border-subtle); cursor: pointer; margin-bottom: 24px; }
.al__now-art { width: 56px; height: 56px; border-radius: 10px; flex: 0 0 auto; display: block; }
.al__now-meta { flex: 1; min-width: 0; }
.al__now-eyebrow { font-size: 10px; color: var(--text-tertiary); }
.al__now-title { font-family: var(--font-display); font-weight: 500; font-size: 16px; color: var(--text-primary); }
.al__now-mood { font-size: 13px; }
.al__now-play { width: 44px; height: 44px; border-radius: 50%; background: none; border: 0; color: var(--accent-primary); cursor: pointer; display: grid; place-items: center; }
.mono { font-family: var(--font-mono); }
.al__h { font-family: var(--font-display); font-weight: 600; font-size: 15px; margin: 22px 0 10px; }
.al__row { display: flex; gap: 14px; overflow-x: auto; padding-bottom: 6px; }
.al__card { flex: 0 0 auto; width: 132px; background: none; border: 0; cursor: pointer; text-align: left; display: flex; flex-direction: column; gap: 6px; }
.al__sq { position: relative; width: 132px; height: 132px; border-radius: 12px; display: block; }
.al__count, .al__dur { position: absolute; left: 8px; bottom: 8px; background: rgba(0,0,0,0.7); color: #fff; padding: 1px 6px; border-radius: 999px; font-size: 10px; }
.al__dur { left: auto; right: 8px; }
.al__gen { position: absolute; inset: 0; display: grid; place-items: center; color: var(--text-secondary); font-size: 11px; background: color-mix(in srgb, var(--brain-amber-surface) 85%, transparent); border-radius: 12px; }
.al__name { font-size: 13px; font-weight: 500; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.al__sub { font-size: 11px; }
.al__brain { display: flex; align-items: center; gap: 12px; width: 100%; padding: 10px 12px; margin-bottom: 10px; border: 1px solid var(--border-subtle); border-left: 3px solid var(--brain-amber); border-radius: 12px; background: var(--background-surface); cursor: pointer; text-align: left; }
.al__brain-art { width: 48px; height: 48px; border-radius: 8px; flex: 0 0 auto; display: block; }
.al__brain-meta { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.al__brain-title { font-family: var(--font-display); font-weight: 500; font-size: 15px; color: var(--text-primary); }
.al__brain-from { font-size: 13px; color: var(--brain-amber); }
.al__brain-dur { font-size: 11px; color: var(--text-tertiary); }
.al__empty { border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--background-surface); padding: 40px; text-align: center; margin-top: 24px; }
.al__empty-title { font-family: var(--font-display); font-weight: 600; font-size: 16px; color: var(--text-secondary); }
</style>
