<script setup lang="ts">
/**
 * Immersive STORIES player overlay. Controls appear on tap/move and auto-hide
 * after 3s. Uses real episode/film data from the API.
 * Video playback: wires to video_url when available, else simulates progress.
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import type { StoryItem, StoryEpisode } from '../../composables/useStories'
import { stFmt, postProgress } from '../../composables/useStories'
import { ShareButton } from '../ui'

const props = defineProps<{ item: StoryItem; ep?: number }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'play', item: StoryItem, ep?: number): void }>()

const progress = ref(0) // 0–100
const playing = ref(true)
const controlsVisible = ref(true)
let tick: number | undefined
let hideTimer: number | undefined

const episode = computed<StoryEpisode | undefined>(() =>
  props.item.episodes?.find((e) => e.episode_number === props.ep),
)

const title = computed(() =>
  episode.value
    ? `${props.item.title} · E${episode.value.episode_number} ${episode.value.title}`
    : props.item.title,
)

const totalSecs = computed(() => {
  if (episode.value?.duration_seconds) return episode.value.duration_seconds
  if (props.item.duration_seconds) return props.item.duration_seconds
  return 1440 // 24min fallback
})

const curSecs = computed(() => Math.round(totalSecs.value * progress.value / 100))

const leftLabel = computed(() => `${stFmt(totalSecs.value - curSecs.value)} left`)

// Determine video URL
const videoUrl = computed(() => episode.value?.video_url ?? props.item.video_url ?? null)

// Share targets the episode when playing one, else the film.
const shareKind = computed<'stories_episode' | 'stories_film'>(() =>
  episode.value ? 'stories_episode' : 'stories_film',
)
const shareRefId = computed(() => episode.value?.id ?? props.item.id)

// Next episode in a series, if any.
const nextEp = computed<StoryEpisode | undefined>(() => {
  if (!episode.value || !props.item.episodes) return undefined
  return props.item.episodes.find((e) => e.episode_number === episode.value!.episode_number + 1)
})
const nextDismissed = ref(false)
const showNextPrompt = computed(() => !!nextEp.value && progress.value >= 92 && !nextDismissed.value)

// Progress reporting (throttled)
let lastReportedPct = 0
function maybeReportProgress() {
  if (Math.abs(progress.value - lastReportedPct) < 5) return
  lastReportedPct = progress.value
  const contentType = episode.value ? 'episode' : 'film'
  const contentId = episode.value?.id ?? props.item.id
  postProgress({
    content_type: contentType,
    content_id: contentId,
    position_seconds: curSecs.value,
    duration_seconds: totalSecs.value,
  }).catch(() => { /* best-effort */ })
}

function startTick() {
  stopTick()
  if (!playing.value) return
  tick = window.setInterval(() => {
    progress.value = Math.min(100, progress.value + 0.5)
    maybeReportProgress()
    if (progress.value >= 100) stopTick()
  }, 250)
}
function stopTick() {
  if (tick) { clearInterval(tick); tick = undefined }
}
function toggle() {
  playing.value = !playing.value
  playing.value ? startTick() : stopTick()
  bump()
}
function seekBy(secs: number) {
  progress.value = Math.max(0, Math.min(100, progress.value + (secs / totalSecs.value) * 100))
  bump()
}
function seekTo(e: MouseEvent) {
  const el = e.currentTarget as HTMLElement
  const r = el.getBoundingClientRect()
  progress.value = Math.max(0, Math.min(100, ((e.clientX - r.left) / r.width) * 100))
  bump()
}
function bump() {
  controlsVisible.value = true
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = window.setTimeout(() => { controlsVisible.value = false }, 3000)
}
function playNext() {
  if (nextEp.value) emit('play', props.item, nextEp.value.episode_number)
}

onMounted(() => { startTick(); bump() })
onBeforeUnmount(() => {
  stopTick()
  if (hideTimer) clearTimeout(hideTimer)
  // Final progress report on unmount
  maybeReportProgress()
})
</script>

<template>
  <div class="stp" @mousemove="bump">
    <!-- If a real video URL exists, embed it -->
    <video
      v-if="videoUrl"
      class="stp__video"
      :src="videoUrl"
      autoplay
      controls
      @click.stop
    />
    <div v-else class="stp__stage" @click="toggle">
      <div class="stp__scrim stp__scrim--top" />
      <div class="stp__scrim stp__scrim--bottom" />
    </div>

    <transition name="fade">
      <div v-show="controlsVisible" class="stp__controls">
        <!-- top bar -->
        <div class="stp__top">
          <button class="stp__icon" aria-label="Exit" @click.stop="emit('close')">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M15 18l-6-6 6-6" /></svg>
          </button>
          <span class="stp__title">{{ title }}</span>
          <ShareButton
            class="stp__share"
            :kind="shareKind"
            :ref-id="shareRefId"
            :text="title"
            @click.stop
          />
        </div>

        <!-- center transport (only shown for simulated playback) -->
        <div v-if="!videoUrl" class="stp__center" @click.stop>
          <button class="stp__seek" aria-label="Back 10s" @click="seekBy(-10)">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4V1L8 5l4 4V6a6 6 0 1 1-6 6" /></svg>
          </button>
          <button class="stp__play" aria-label="Play/pause" @click="toggle">
            <svg v-if="playing" width="30" height="30" viewBox="0 0 24 24" fill="currentColor"><path d="M6 4h4v16H6zM14 4h4v16h-4z" /></svg>
            <svg v-else width="30" height="30" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
          </button>
          <button class="stp__seek" aria-label="Forward 10s" @click="seekBy(10)">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="transform: scaleX(-1)"><path d="M12 4V1L8 5l4 4V6a6 6 0 1 1-6 6" /></svg>
          </button>
        </div>

        <!-- bottom bar (simulated only) -->
        <div v-if="!videoUrl" class="stp__bottom" @click.stop>
          <div class="stp__bar" @click="seekTo">
            <div class="stp__bar-fill" :style="{ width: progress + '%' }" />
            <div class="stp__bar-thumb" :style="{ left: progress + '%' }" />
          </div>
          <div class="stp__meta">
            <span class="mono">{{ stFmt(curSecs) }} / {{ stFmt(totalSecs) }}</span>
            <span class="mono stp__left">{{ leftLabel }}</span>
          </div>
        </div>
      </div>
    </transition>

    <!-- next-episode prompt -->
    <transition name="slide">
      <div v-if="showNextPrompt" class="stp__next">
        <div class="stp__next-label">Up next</div>
        <div class="stp__next-title">E{{ nextEp!.episode_number }} · {{ nextEp!.title }}</div>
        <div class="stp__next-actions">
          <button class="stp__next-btn stp__next-btn--primary" @click="playNext">Play now</button>
          <button class="stp__next-btn" @click="nextDismissed = true">Cancel</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.stp { position: fixed; inset: 0; z-index: 200; background: #000; color: #fff; }
.stp__video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.stp__stage { position: absolute; inset: 0; background: radial-gradient(circle at 50% 35%, #1a1a28, #000); cursor: pointer; }
.stp__scrim { position: absolute; left: 0; right: 0; height: 120px; pointer-events: none; }
.stp__scrim--top { top: 0; background: linear-gradient(to bottom, rgba(0,0,0,0.7), transparent); }
.stp__scrim--bottom { bottom: 0; background: linear-gradient(to top, rgba(0,0,0,0.8), transparent); }
.stp__controls { position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: space-between; padding: 20px; pointer-events: none; z-index: 10; }
.stp__controls > * { pointer-events: auto; }
.stp__top { display: flex; align-items: center; gap: 12px; }
.stp__title { font-family: var(--font-display); font-weight: 600; font-size: 15px; }
.stp__share { margin-left: auto; color: rgba(255,255,255,0.85); }
.stp__icon { background: none; border: 0; color: #fff; cursor: pointer; display: flex; }
.stp__center { display: flex; align-items: center; justify-content: center; gap: 40px; }
.stp__seek { background: none; border: 0; color: #fff; cursor: pointer; display: flex; }
.stp__play { width: 64px; height: 64px; border-radius: 50%; background: var(--accent-primary); color: #fff; border: 0; cursor: pointer; display: grid; place-items: center; }
.stp__bottom { display: flex; flex-direction: column; gap: 8px; }
.stp__bar { position: relative; height: 4px; border-radius: 999px; background: rgba(255,255,255,0.25); cursor: pointer; }
.stp__bar-fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 999px; background: var(--brain-amber); }
.stp__bar-thumb { position: absolute; top: 50%; width: 12px; height: 12px; border-radius: 50%; background: #fff; transform: translate(-50%, -50%); }
.stp__meta { display: flex; justify-content: space-between; font-size: 12px; color: rgba(255,255,255,0.8); }
.mono { font-family: var(--font-mono); }
.stp__next { position: absolute; right: 20px; bottom: 110px; width: 260px; padding: 14px; border-radius: 12px; background: rgba(20,20,30,0.7); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.12); z-index: 10; }
.stp__next-label { font-family: var(--font-mono); font-size: 11px; color: rgba(255,255,255,0.7); }
.stp__next-title { font-family: var(--font-display); font-weight: 600; font-size: 14px; margin: 4px 0 10px; }
.stp__next-actions { display: flex; gap: 8px; }
.stp__next-btn { flex: 1; height: 34px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); background: transparent; color: #fff; cursor: pointer; font-size: 13px; }
.stp__next-btn--primary { background: var(--accent-primary); border-color: var(--accent-primary); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-enter-active { transition: transform 0.3s, opacity 0.3s; }
.slide-enter-from { transform: translateX(20px); opacity: 0; }
</style>
