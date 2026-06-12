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
        <span class="overlay-text">RENDERING...</span>
        <div class="render-track"><div class="render-fill" /></div>
      </div>
      <div v-else-if="isFailed" class="thumb-overlay thumb-overlay--failed">
        <span class="overlay-text overlay-text--failed">GENERATION FAILED</span>
      </div>
      <span v-else class="duration-tag">{{ duration }}</span>
    </div>

    <div class="card-meta">
      <div class="card-title">{{ video.title }}</div>
      <div class="card-sub">
        <span class="card-creator">{{ video.creator_name.toUpperCase() }}</span>
        <span class="card-dot">·</span>
        <span>{{ duration }}</span>
        <span class="card-score">[{{ video.score.toFixed(2) }}]</span>
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
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 0;
  padding: 0;
  cursor: pointer;
  transition: border-color 0.12s ease;
}
.video-card:hover:not(:disabled)  { border-color: var(--accent); }
.video-card--active               { border-color: var(--accent); }
.video-card--failed               { border-color: var(--status-error); }
.video-card:disabled              { cursor: default; opacity: 0.75; }

/* ── Thumbnail ──────────────────────────────────────────────────────────── */
.thumb-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-bottom: 1px solid var(--border);
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
  background: repeating-linear-gradient(90deg, #12121a 0px, #1e1e2e 40px, #12121a 80px);
}
.thumb-placeholder {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-3);
  letter-spacing: 0.2em;
}

.thumb-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(10, 10, 15, 0.78);
  padding: 0 16px;
}
.thumb-overlay--failed { background: rgba(30, 8, 8, 0.82); }

.overlay-text {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--text-2);
}
.overlay-text--failed { color: var(--status-error); }

.render-track {
  width: 70%;
  height: 2px;
  background: var(--border);
  overflow: hidden;
}
.render-fill {
  height: 100%;
  width: 40%;
  background: var(--accent);
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
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--text-1);
  background: rgba(10, 10, 15, 0.85);
  border: 1px solid var(--border);
  padding: 1px 5px;
}

/* ── Meta ───────────────────────────────────────────────────────────────── */
.card-meta {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 10px 12px;
}
.card-title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--text-1);
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
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--text-3);
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
  color: var(--accent-2);
}

@media (prefers-reduced-motion: reduce) { .render-fill { animation: none; } }
</style>
