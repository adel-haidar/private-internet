<script setup lang="ts">
import { computed } from 'vue'
import type { Video } from '../composables/useContent'

const props = defineProps<{
  video: Video
  active?: boolean
}>()

defineEmits<{ select: [video: Video] }>()

const duration = computed(() => {
  const s = props.video.duration_seconds
  if (s === null || s === undefined) return '—:——'
  const m = Math.floor(s / 60)
  const r = Math.round(s % 60)
  return `${m}:${String(r).padStart(2, '0')}`
})

const isReady      = computed(() => props.video.status === 'ready')
const isFailed     = computed(() => props.video.status === 'failed')
const isProcessing = computed(() => props.video.status === 'processing' || props.video.status === 'pending')
</script>

<template>
  <button
    class="video-card"
    :class="{ 'video-card--active': active, 'video-card--failed': isFailed }"
    :disabled="!isReady"
    @click="$emit('select', video)"
  >
    <div class="thumb-wrap">
      <img
        v-if="video.thumbnail_url"
        class="thumb"
        :src="video.thumbnail_url"
        :alt="video.title"
        loading="lazy"
      />
      <div v-else class="thumb thumb--empty">
        <span class="thumb-placeholder">███ ██ ████</span>
      </div>

      <div v-if="isProcessing" class="thumb-overlay">
        <span class="overlay-text">Rendering…</span>
        <div class="render-track"><div class="render-fill" /></div>
      </div>
      <div v-else-if="isFailed" class="thumb-overlay thumb-overlay--failed">
        <span class="overlay-text overlay-text--failed">Generation failed</span>
      </div>
      <span v-else class="duration-tag">{{ duration }}</span>
    </div>

    <div class="card-meta">
      <div class="card-title">{{ video.title }}</div>
      <div class="card-sub">
        <span class="card-creator">{{ video.creator_name }}</span>
        <span class="card-dot">·</span>
        <span>{{ duration }}</span>
        <span class="card-score">{{ video.score.toFixed(2) }}</span>
      </div>
    </div>
  </button>
</template>

<style scoped>
.video-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  text-align: left;
  background: var(--background-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 12px);
  padding: 0;
  cursor: pointer;
  overflow: hidden;
  transition: border-color 0.15s ease;
}
.video-card:hover:not(:disabled)  { border-color: var(--accent-primary); }
.video-card--active               { border-color: var(--accent-primary); }
.video-card--failed               { border-color: var(--danger); }
.video-card:disabled              { cursor: default; opacity: 0.75; }

/* ── Thumbnail ──────────────────────────────────────────────────────────── */
.thumb-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-bottom: 1px solid var(--border-subtle);
}
.thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.thumb--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--background-raised);
}
.thumb-placeholder {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-tertiary);
}

.thumb-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.65);
  padding: 0 16px;
}
.thumb-overlay--failed { background: rgba(0, 0, 0, 0.75); }

.overlay-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
}
.overlay-text--failed { color: var(--danger); }

.render-track {
  width: 70%;
  height: 2px;
  background: rgba(255,255,255,0.2);
  overflow: hidden;
}
.render-fill {
  height: 100%;
  width: 40%;
  background: var(--accent-primary);
  animation: renderSweep 1.6s ease-in-out infinite;
}
@keyframes renderSweep {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(280%); }
}

.duration-tag {
  position: absolute;
  right: 6px;
  bottom: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.9);
  background: rgba(0, 0, 0, 0.65);
  border-radius: var(--radius-sm, 8px);
  padding: 1px 6px;
}

/* ── Meta ───────────────────────────────────────────────────────────────── */
.card-meta {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 10px 12px;
}
.card-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-sub {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 12px;
  color: var(--text-tertiary);
  min-width: 0;
}
.card-creator {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card-dot { flex: 0 0 auto; }
.card-score {
  margin-left: auto;
  flex: 0 0 auto;
  color: var(--brain-amber);
  font-family: var(--font-mono);
}

@media (prefers-reduced-motion: reduce) { .render-fill { animation: none; } }
</style>
