<script setup lang="ts">
/**
 * StoryHero — Featured hero, landscape letterboxed with 4% black bars.
 * Uses category chip (from real API), premise, duration.
 * genre/score/year removed — not in real API.
 */
import type { StoryItem } from '../../composables/useStories'
import { stPosterStyle, stDurLabel } from '../../composables/useStories'

const props = defineProps<{
  item: StoryItem
}>()

const emit = defineEmits<{
  (e: 'play'): void
  (e: 'open'): void
}>()
</script>

<template>
  <div
    class="st-hero"
    :style="item.poster_url || item.thumbnail_url
      ? { backgroundImage: `url(${item.poster_url ?? item.thumbnail_url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
      : stPosterStyle(item.title)"
  >
    <!-- 4% letterbox bars -->
    <div class="st-hero__bar st-hero__bar--top" />
    <div class="st-hero__bar st-hero__bar--bot" />
    <!-- cinematic scrim -->
    <div class="st-cine" />
    <!-- top row: category chip + FILM badge -->
    <div class="st-hero__top">
      <span v-if="item.category" class="st-chip">{{ item.category.toUpperCase().slice(0, 8) }}</span>
      <span v-else class="st-chip" style="opacity: 0">FILM</span>
      <span class="t-mono" style="font-size: var(--text-xs); color: rgba(255,255,255,0.7)">FILM</span>
    </div>
    <!-- body -->
    <div class="st-hero__body">
      <div class="st-hero__title">{{ item.title }}</div>
      <p v-if="item.premise" class="t-serif st-hero__premise">{{ item.premise }}</p>
      <div class="st-hero__actions">
        <button class="pi-btn pi-btn--primary" @click="emit('play')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>
          Play
        </button>
        <button
          class="pi-btn pi-btn--ghost"
          style="color: #fff; border-color: rgba(255,255,255,0.3)"
          @click="emit('open')"
        >More info</button>
        <span v-if="item.duration_seconds" class="t-mono" style="font-size: var(--text-xs); color: rgba(255,255,255,0.7)">
          {{ stDurLabel(item.duration_seconds) }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.st-hero {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  min-height: 320px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  background: var(--background-raised);
  transition: transform 0.12s var(--ease);
}
.st-hero:hover .st-hero__play-icon { opacity: 1; }

.st-hero__bar {
  position: absolute;
  left: 0; right: 0;
  height: 4%;
  background: #000;
  z-index: 2;
}
.st-hero__bar--top { top: 0; }
.st-hero__bar--bot { bottom: 0; }

.st-cine {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(12,12,20,0.92) 0%, rgba(12,12,20,0.60) 40%, rgba(12,12,20,0) 100%);
  z-index: 1;
}

.st-hero__top {
  position: absolute;
  top: var(--space-5);
  left: var(--space-5);
  right: var(--space-5);
  z-index: 3;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.st-hero__body {
  position: relative;
  z-index: 3;
  padding: var(--space-8);
  max-width: 60%;
}

.st-hero__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--text-xl);
  color: #fff;
  line-height: 1.15;
  letter-spacing: -0.01em;
}

.st-hero__premise {
  font-size: var(--text-base);
  color: rgba(255,255,255,0.82);
  margin-top: var(--space-3);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.st-hero__actions {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-top: var(--space-5);
}

.st-chip {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--brain-amber-surface);
  color: var(--brain-amber);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

/* shared button primitives */
.pi-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  height: 36px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-weight: 500;
  font-size: var(--text-sm);
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s, color 0.12s;
}
.pi-btn--primary {
  background: var(--accent-primary);
  color: #fff;
  border-color: var(--accent-primary);
}
.pi-btn--primary:hover { background: var(--accent-hover); }
.pi-btn--ghost {
  background: transparent;
  border-color: var(--border-medium);
  color: var(--text-secondary);
}
.pi-btn--ghost:hover { border-color: var(--border-strong); color: var(--text-primary); }

@media (max-width: 1024px) {
  .st-hero__body { max-width: 100%; }
}
</style>
