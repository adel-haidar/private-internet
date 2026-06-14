<script setup lang="ts">
/** Slide-in filter panel for PULSE: Sort (server) + Tone + Creator (client). */
import type { PostSort, Tone } from '../../composables/useContent'
import FeedChip from './FeedChip.vue'

defineProps<{
  sort: PostSort
  tone: Tone | 'all'
  creator: string | null
  creators: { id: string; name: string }[]
}>()
const emit = defineEmits<{
  (e: 'update:sort', v: PostSort): void
  (e: 'update:tone', v: Tone | 'all'): void
  (e: 'update:creator', v: string | null): void
  (e: 'close'): void
}>()

const SORTS: { v: PostSort; label: string }[] = [
  { v: 'latest', label: 'Latest' },
  { v: 'top', label: 'Top score' },
  { v: 'unrated', label: 'Unrated' },
]
const TONES: (Tone | 'all')[] = ['all', 'informative', 'satirical', 'critical', 'supportive']
const TONE_COLOR: Record<string, string> = {
  all: 'var(--accent-primary)',
  informative: 'var(--accent-primary)',
  satirical: 'var(--brain-amber)',
  critical: 'var(--danger)',
  supportive: 'var(--success)',
}
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
</script>

<template>
  <div class="fp__overlay" @click.self="emit('close')">
    <aside class="fp">
      <div class="fp__head">
        <span class="fp__title">Filter Pulse</span>
        <button class="fp__x" @click="emit('close')" aria-label="Close">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      </div>

      <div class="fp__group">
        <div class="fp__label t-mono">Sort</div>
        <div class="fp__chips">
          <FeedChip v-for="s in SORTS" :key="s.v" :label="s.label" :active="sort === s.v" @click="emit('update:sort', s.v)" />
        </div>
      </div>

      <div class="fp__group">
        <div class="fp__label t-mono">Tone</div>
        <div class="fp__chips">
          <FeedChip v-for="t in TONES" :key="t" :label="cap(t)" :color="TONE_COLOR[t]" :active="tone === t" @click="emit('update:tone', t)" />
        </div>
      </div>

      <div class="fp__group">
        <div class="fp__label t-mono">Creator</div>
        <div class="fp__chips">
          <FeedChip label="All" :active="creator === null" @click="emit('update:creator', null)" />
          <FeedChip v-for="c in creators" :key="c.id" :label="c.name" :active="creator === c.id" @click="emit('update:creator', c.id)" />
        </div>
      </div>

      <button class="fp__done" @click="emit('close')">Show results</button>
    </aside>
  </div>
</template>

<style scoped>
.fp__overlay { position: fixed; inset: 0; z-index: 95; background: rgba(0,0,0,0.25); display: flex; justify-content: flex-end; animation: fade 0.15s ease; }
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
.fp { width: 360px; max-width: 90vw; height: 100%; background: var(--background-surface); border-left: 1px solid var(--border-subtle); padding: 24px; overflow-y: auto; }
.fp__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.fp__title { font-family: var(--font-display); font-weight: 600; font-size: var(--text-md); color: var(--text-primary); }
.fp__x { background: none; border: 0; color: var(--text-secondary); cursor: pointer; display: flex; }
.fp__group { margin-bottom: 20px; }
.fp__label { font-size: var(--text-xs); font-weight: 600; color: var(--text-tertiary); margin-bottom: 8px; text-transform: uppercase; }
.fp__chips { display: flex; flex-wrap: wrap; gap: 8px; }
.fp__done { width: 100%; height: 44px; border: 0; border-radius: var(--radius-sm); background: var(--accent-primary); color: #fff; font-family: var(--font-display); font-weight: 600; font-size: var(--text-sm); cursor: pointer; margin-top: 8px; }
</style>
