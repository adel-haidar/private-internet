<script setup lang="ts">
/** A standard SIGNAL video card: 16:9 thumbnail (seeded fallback) + duration
 * badge, 2-line title, creator · duration, score. Tap the card to play. */
import { computed } from 'vue'
import type { Video } from '../../composables/useContent'
import ScoreText from './ScoreText.vue'
import BrainPulse from '../ui/BrainPulse.vue'
import { seededThumb } from './seeded'
import { fmtSecs, isProcessing } from './video-util'

const props = withDefaults(defineProps<{ video: Video; width?: number }>(), { width: 220 })
defineEmits<{ (e: 'play'): void }>()

const processing = computed(() => isProcessing(props.video))
const dur = computed(() => fmtSecs(props.video.duration_seconds))
</script>

<template>
  <button class="vc" :style="{ width: width + 'px' }" :disabled="processing" @click="$emit('play')">
    <span class="vc__thumb" :style="video.thumbnail_url ? { backgroundImage: `url(${video.thumbnail_url})` } : seededThumb(video.creator_name)">
      <span v-if="processing" class="vc__proc">
        <BrainPulse :size="24" />
        <span class="vc__proctxt">Rendering…</span>
      </span>
      <span v-else-if="dur" class="vc__dur t-mono">{{ dur }}</span>
    </span>
    <span class="vc__title">{{ video.title }}</span>
    <span class="vc__meta">
      <span class="vc__creator">{{ video.creator_name.split(' ')[0] }} · <span class="t-mono">{{ dur }}</span></span>
      <ScoreText v-if="!processing" :score="video.score" />
    </span>
  </button>
</template>

<style scoped>
.vc { flex: 0 0 auto; background: none; border: 0; padding: 0; text-align: left; cursor: pointer; display: flex; flex-direction: column; gap: 8px; }
.vc:disabled { cursor: default; }
.vc__thumb { position: relative; aspect-ratio: 16/9; border-radius: var(--radius-sm); background-size: cover; background-position: center; overflow: hidden; }
.vc__dur { position: absolute; right: 6px; bottom: 6px; padding: 1px 6px; border-radius: 999px; background: rgba(0,0,0,0.78); color: #fff; font-family: var(--font-mono); font-size: 10px; }
.vc__proc { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; background: color-mix(in srgb, var(--brain-amber-surface) 85%, transparent); }
.vc__proctxt { font-size: var(--text-xs); color: var(--text-secondary); }
.vc__title { font-size: var(--text-sm); font-weight: 500; line-height: 1.35; color: var(--text-primary); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.vc__meta { display: flex; align-items: center; gap: 6px; }
.vc__creator { flex: 1; min-width: 0; font-size: var(--text-xs); color: var(--text-tertiary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
