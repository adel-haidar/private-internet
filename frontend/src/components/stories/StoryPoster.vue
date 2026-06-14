<script setup lang="ts">
/**
 * StoryPoster — 2:3 portrait poster card.
 * Adapted for the real API: uses category (not genre), duration_seconds (not dur),
 * no score badge. Falls back to gradient if no thumbnail_url/poster_url.
 */
import { computed } from 'vue'
import type { StoryItem } from '../../composables/useStories'
import { stPosterStyle, stDurLabel } from '../../composables/useStories'
import BrainPulse from '../ui/BrainPulse.vue'

const props = defineProps<{
  item: StoryItem
  showProgress?: boolean
  wide?: boolean
}>()

const emit = defineEmits<{
  (e: 'click'): void
}>()

const isGenerating = computed(() => props.item.status === 'generating')
const isSeries = computed(() => props.item.kind === 'series')

const posterStyle = computed(() => {
  if (isGenerating.value) return {}
  if (props.item.poster_url || props.item.thumbnail_url) {
    return {
      backgroundImage: `url(${props.item.poster_url ?? props.item.thumbnail_url})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    }
  }
  return stPosterStyle(props.item.title || props.item.id)
})

const categoryChip = computed(() => {
  const c = props.item.category
  if (!c) return ''
  return c.toUpperCase().slice(0, 8)
})

const durLabel = computed(() => stDurLabel(props.item.duration_seconds))

const progressPct = computed(() => {
  const wp = props.item.watch_progress
  if (!wp || !wp.duration_seconds) return null
  return Math.min(100, Math.round((wp.position_seconds / wp.duration_seconds) * 100))
})

const epCount = computed(() => props.item.episode_count ?? 0)
</script>

<template>
  <button
    class="st-poster-card"
    :class="{ 'st-poster-card--wide': wide }"
    :disabled="isGenerating"
    @click="emit('click')"
  >
    <div class="st-poster" :style="posterStyle">
      <!-- Generating state -->
      <template v-if="isGenerating">
        <div class="st-poster__gen">
          <BrainPulse :size="24" />
          <span class="t-secondary" style="font-size: var(--text-xs)">Generating…</span>
        </div>
      </template>

      <!-- Normal state -->
      <template v-else>
        <div class="st-poster__scrim" />
        <span v-if="categoryChip" class="st-poster__genre">{{ categoryChip }}</span>
        <span v-if="isSeries" class="st-poster__badge">SERIES</span>
        <span v-else-if="durLabel" class="st-poster__dur">{{ durLabel }}</span>
        <span class="st-poster__play" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>
        </span>
        <div class="st-poster__title">{{ item.title }}</div>
        <div v-if="showProgress && progressPct != null" class="st-poster__prog">
          <span :style="{ width: progressPct + '%' }" />
        </div>
      </template>
    </div>

    <!-- Below-poster metadata -->
    <div class="st-pmeta">
      <div class="st-pmeta__title">
        {{ isGenerating ? 'New film' : item.title }}
      </div>
      <div class="st-pmeta__sub">
        <span v-if="isGenerating" class="t-tertiary">Generating…</span>
        <span
          v-else-if="isSeries"
          class="t-mono"
          style="font-size: var(--text-xs); color: var(--text-tertiary)"
        >{{ epCount ? `${epCount} episodes` : 'Series' }}</span>
        <span
          v-else-if="showProgress && item.watch_progress"
          class="t-mono"
          style="font-size: var(--text-xs); color: var(--text-tertiary)"
        >{{ Math.round(Math.max(0, item.watch_progress.duration_seconds - item.watch_progress.position_seconds) / 60) }}m left</span>
        <span
          v-else-if="durLabel"
          class="t-mono"
          style="font-size: var(--text-xs); color: var(--text-tertiary)"
        >{{ durLabel }}</span>
      </div>
    </div>
  </button>
</template>

<style scoped>
.st-poster-card {
  flex: 0 0 auto;
  width: 168px;
  background: none;
  text-align: left;
  scroll-snap-align: start;
  transition: transform 0.12s var(--ease);
  cursor: pointer;
  border: none;
  padding: 0;
}
.st-poster-card--wide { width: 200px; }
.st-poster-card:hover:not(:disabled) { transform: translateY(-2px); }
.st-poster-card:active:not(:disabled) { transform: scale(0.96); }
.st-poster-card:disabled { opacity: 0.7; cursor: default; }

.st-poster {
  position: relative;
  aspect-ratio: 2/3;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--background-raised);
}
.st-poster__scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(8,8,14,0.86) 2%, rgba(8,8,14,0.12) 44%, transparent 72%);
}
.st-poster__genre {
  position: absolute;
  top: 9px;
  left: 9px;
  z-index: 2;
  padding: 2px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--brain-amber-surface) 85%, transparent);
  color: var(--brain-amber);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
}
.st-poster__dur,
.st-poster__badge {
  position: absolute;
  z-index: 2;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(0,0,0,0.7);
  color: #fff;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}
.st-poster__dur { bottom: 9px; right: 9px; }
.st-poster__badge { top: 9px; right: 9px; }
.st-poster__title {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 16px;
  z-index: 1;
  color: #fff;
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--text-md);
  line-height: 1.15;
  letter-spacing: -0.01em;
  text-shadow: 0 1px 14px rgba(0,0,0,0.55);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.st-poster__prog {
  position: absolute;
  left: 0; right: 0; bottom: 0;
  z-index: 3;
  height: 3px;
  background: rgba(0,0,0,0.4);
}
.st-poster__prog > span {
  display: block;
  height: 100%;
  background: var(--brain-amber);
  transition: width 0.3s var(--ease);
}
.st-poster__gen {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: var(--brain-amber-surface);
}
.st-poster__play {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0.9);
  z-index: 2;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(255,255,255,0.18);
  border: 1px solid rgba(255,255,255,0.3);
  display: grid;
  place-items: center;
  color: #fff;
  opacity: 0;
  transition: opacity 0.15s var(--ease), transform 0.15s var(--ease);
}
.st-poster-card:hover .st-poster__play { opacity: 1; transform: translate(-50%,-50%) scale(1); }

.st-pmeta { margin-top: var(--space-3); }
.st-pmeta__title {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: var(--text-base);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.st-pmeta__sub {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-top: 2px;
}
</style>
