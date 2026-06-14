<script setup lang="ts">
/**
 * Full-screen Now Playing overlay (toggled by useAria().nowOpen). Ambient
 * mood-tint background, album-art hero that scales on play/pause, seekable
 * waveform, transport, and Player | Lyrics tabs. Queue listed below.
 */
import { ref, computed } from 'vue'
import {
  useAria, arArtBackground, arBars, arFmt, arSecs, AR_MOOD_COLOR,
} from '../../composables/useAria'

const {
  track, playing, progress, nowOpen, shuffle, repeat, queue,
  isLiked, toggle, next, prev, seek, toggleLike, closeNow, setShuffle, setRepeat,
  getTrack,
} = useAria()

const tab = ref<'player' | 'lyrics'>('player')

const total = computed(() => (track.value ? arSecs(track.value) : 0))
const cur = computed(() => Math.round(total.value * progress.value / 100))
const bars = computed(() => (track.value ? arBars(track.value.id, 64) : []))
const queueTracks = computed(() => queue.value.map((id) => getTrack(id)).filter(Boolean))

function seekBars(e: MouseEvent) {
  const el = e.currentTarget as HTMLElement
  const r = el.getBoundingClientRect()
  seek(((e.clientX - r.left) / r.width) * 100)
}
function seekBy(secs: number) {
  seek(progress.value + (secs / total.value) * 100)
}
</script>

<template>
  <transition name="np-fade">
    <div v-if="nowOpen && track" class="np" :style="{ '--mood': AR_MOOD_COLOR[track.mood] }">
      <div class="np__tint" />
      <div class="np__inner">
        <div class="np__top">
          <button class="np__icon" aria-label="Collapse" @click="closeNow">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg>
          </button>
          <span class="np__eyebrow mono">Now playing</span>
          <span style="width:24px" />
        </div>

        <div class="np__art" :class="{ 'np__art--paused': !playing }" :style="arArtBackground(track)" />

        <div class="np__head">
          <div class="np__title">{{ track.title }}</div>
          <button class="np__like" :class="{ 'np__like--on': isLiked(track.id) }" aria-label="Like" @click="toggleLike(track.id)">
            <svg width="26" height="26" viewBox="0 0 24 24" :fill="isLiked(track.id) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.7"><path d="M20.8 5.6a5.5 5.5 0 0 0-7.8 0L12 6.6l-1-1a5.5 5.5 0 1 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>
          </button>
        </div>
        <div class="np__chips">
          <span class="np__mood" :style="{ color: AR_MOOD_COLOR[track.mood], background: 'color-mix(in srgb, ' + AR_MOOD_COLOR[track.mood] + ' 15%, transparent)' }">{{ track.mood }}</span>
          <span v-if="track.topic" class="np__from">from: {{ track.topic }}</span>
        </div>

        <div class="np__tabs">
          <button :class="['np__tab', tab === 'player' && 'np__tab--on']" @click="tab = 'player'">Player</button>
          <button :class="['np__tab', tab === 'lyrics' && 'np__tab--on']" @click="tab = 'lyrics'">Lyrics</button>
        </div>

        <template v-if="tab === 'player'">
          <div class="np__wave" @click="seekBars">
            <span
              v-for="(h, i) in bars" :key="i" class="np__bar"
              :style="{ height: (12 + h * 36) + 'px', background: (i / bars.length * 100) <= progress ? 'var(--accent-primary)' : 'var(--border-medium)' }"
            />
          </div>
          <div class="np__times"><span class="mono">{{ arFmt(cur) }}</span><span class="mono">{{ arFmt(total) }}</span></div>
          <div class="np__transport">
            <button class="np__t" aria-label="Previous" @click="prev"><svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h2v14H6zM20 5v14l-9-7z"/></svg></button>
            <button class="np__t" aria-label="Back 10s" @click="seekBy(-10)"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4V1L8 5l4 4V6a6 6 0 1 1-6 6"/></svg></button>
            <button class="np__play" aria-label="Play/pause" @click="toggle">
              <svg v-if="playing" width="30" height="30" viewBox="0 0 24 24" fill="currentColor"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg>
              <svg v-else width="30" height="30" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
            </button>
            <button class="np__t" aria-label="Forward 10s" @click="seekBy(10)"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="transform:scaleX(-1)"><path d="M12 4V1L8 5l4 4V6a6 6 0 1 1-6 6"/></svg></button>
            <button class="np__t" aria-label="Next" @click="next"><svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M16 5h2v14h-2zM4 5l9 7-9 7z"/></svg></button>
          </div>
          <div class="np__secondary">
            <button :class="['np__sec', shuffle && 'np__sec--on']" aria-label="Shuffle" @click="setShuffle(!shuffle)"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/></svg></button>
            <button :class="['np__sec', repeat && 'np__sec--on']" aria-label="Repeat" @click="setRepeat(!repeat)"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3"/></svg></button>
          </div>
        </template>

        <template v-else>
          <div class="np__lyrics">
            <p v-if="!track.lyrics?.length" class="np__nolyrics">No lyrics for this track.</p>
            <p v-for="(line, i) in track.lyrics" :key="i" class="np__line">{{ line }}</p>
          </div>
        </template>

        <div v-if="queueTracks.length" class="np__queue">
          <div class="np__queue-head mono">Up next · {{ queueTracks.length }}</div>
          <div v-for="(t, i) in queueTracks" :key="i" class="np__qrow">
            <span class="np__qart" :style="t && arArtBackground(t)" />
            <span class="np__qtitle">{{ t?.title }}</span>
            <span class="mono np__qdur">{{ t?.dur }}</span>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.np { position: fixed; inset: 0; z-index: 120; background: var(--background-page); overflow-y: auto; }
.np__tint { position: fixed; inset: 0; background: var(--mood); opacity: 0.16; pointer-events: none; transition: background 0.8s; }
.np__inner { position: relative; max-width: 520px; margin: 0 auto; padding: 16px 24px 48px; }
.np__top { display: flex; align-items: center; justify-content: space-between; }
.np__icon { background: none; border: 0; color: var(--text-primary); cursor: pointer; display: flex; }
.np__eyebrow { font-size: 11px; color: var(--text-tertiary); }
.mono { font-family: var(--font-mono); }
.np__art { width: 300px; height: 300px; max-width: 80%; aspect-ratio: 1; margin: 24px auto; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.25); transition: transform 0.2s ease; display: block; }
.np__art--paused { transform: scale(0.92); }
.np__head { display: flex; align-items: center; gap: 12px; }
.np__title { flex: 1; font-family: var(--font-display); font-weight: 600; font-size: 22px; color: var(--text-primary); }
.np__like { background: none; border: 0; cursor: pointer; color: var(--text-secondary); display: flex; }
.np__like--on { color: var(--brain-amber); }
.np__chips { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
.np__mood { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px; }
.np__from { font-size: 13px; color: var(--text-secondary); }
.np__tabs { display: flex; gap: 20px; margin: 24px 0 16px; }
.np__tab { background: none; border: 0; cursor: pointer; font-family: var(--font-display); font-weight: 500; font-size: 16px; color: var(--text-tertiary); }
.np__tab--on { color: var(--text-primary); }
.np__wave { display: flex; align-items: center; gap: 2px; height: 48px; cursor: pointer; }
.np__bar { flex: 1; border-radius: 2px; }
.np__times { display: flex; justify-content: space-between; margin-top: 6px; font-size: 11px; color: var(--text-tertiary); }
.np__transport { display: flex; align-items: center; justify-content: center; gap: 18px; margin-top: 20px; }
.np__t { background: none; border: 0; cursor: pointer; color: var(--text-secondary); display: flex; }
.np__play { width: 64px; height: 64px; border-radius: 50%; background: var(--accent-primary); color: #fff; border: 0; cursor: pointer; display: grid; place-items: center; }
.np__secondary { display: flex; justify-content: center; gap: 32px; margin-top: 16px; }
.np__sec { background: none; border: 0; cursor: pointer; color: var(--text-tertiary); display: flex; }
.np__sec--on { color: var(--accent-primary); }
.np__lyrics { padding: 8px 0; }
.np__line { font-family: var(--font-serif); font-size: 18px; line-height: 1.7; color: var(--text-primary); margin: 0 0 6px; }
.np__nolyrics { font-family: var(--font-serif); color: var(--text-tertiary); }
.np__queue { margin-top: 28px; border-top: 1px solid var(--border-subtle); padding-top: 16px; }
.np__queue-head { font-size: 11px; color: var(--text-tertiary); margin-bottom: 10px; }
.np__qrow { display: flex; align-items: center; gap: 10px; padding: 6px 0; }
.np__qart { width: 36px; height: 36px; border-radius: 6px; flex: 0 0 auto; display: block; }
.np__qtitle { flex: 1; font-size: 14px; color: var(--text-primary); }
.np__qdur { font-size: 11px; color: var(--text-tertiary); }
.np-fade-enter-active, .np-fade-leave-active { transition: opacity 0.25s; }
.np-fade-enter-from, .np-fade-leave-to { opacity: 0; }
</style>
