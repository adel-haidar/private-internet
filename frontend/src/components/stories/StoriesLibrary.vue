<script setup lang="ts">
/**
 * StoriesLibrary — main landing screen.
 * Sections: Continue watching → Featured hero → New films → Series → By category.
 * Data comes from the real /api/stories endpoint via useStories().
 */
import { computed, onMounted } from 'vue'
import type { StoriesView, StoryItem } from '../../composables/useStories'
import {
  useStories,
  stPosterStyle,
} from '../../composables/useStories'
import StoryPoster from './StoryPoster.vue'
import StorySection from './StorySection.vue'
import StoryHero from './StoryHero.vue'

const emit = defineEmits<{
  (e: 'navigate', v: StoriesView): void
  (e: 'play', item: StoryItem, ep?: number): void
}>()

const { films, series, categories, continueWatching, libraryLoading, libraryError, loadLibrary, navigate: _nav, play: _play } = useStories()

onMounted(() => { loadLibrary() })

// Featured = first ready film
const featured = computed(() => films.value.find((f) => f.status === 'ready') ?? null)

// New films = all ready films except featured
const newFilms = computed(() => films.value.filter((f) => f.status !== 'generating' && f.id !== featured.value?.id))

// Categories with content (excluding featured)
const catsWith = computed(() =>
  categories.value.filter((c) =>
    [...films.value, ...series.value].some((x) => x.category === c.category && x.id !== featured.value?.id)
  )
)

// All items for category rows
const allItems = computed(() => [...films.value, ...series.value])
</script>

<template>
  <div>
    <!-- masthead -->
    <div class="st-head">
      <div>
        <h1 class="st-page-title">Stories</h1>
        <p class="t-secondary" style="font-size: var(--text-base); margin-top: var(--space-2)">
          Long-form films and series, generated from your brain. Something to sit down with.
        </p>
      </div>
      <button class="ghost-btn" @click="emit('navigate', { name: 'search' })">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.3-4.3"/></svg>
        Search
      </button>
    </div>

    <!-- loading -->
    <div v-if="libraryLoading" class="st-loading">Loading your stories…</div>

    <!-- error -->
    <div v-else-if="libraryError" class="st-error">
      <p>Could not load stories: {{ libraryError }}</p>
      <button class="ghost-btn" @click="loadLibrary(true)">Retry</button>
    </div>

    <template v-else>
      <!-- continue watching -->
      <template v-if="continueWatching.length > 0">
        <div class="st-eyebrow" style="margin-bottom: var(--space-3)">Continue watching</div>
        <div class="st-row">
          <button
            v-for="cw in continueWatching"
            :key="cw.content_id"
            class="st-poster-card"
            @click="emit('navigate', { name: cw.content_type === 'film' ? 'film' : 'series', id: cw.content_id })"
          >
            <div
              class="st-poster"
              :style="cw.thumbnail_url
                ? { backgroundImage: `url(${cw.thumbnail_url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
                : stPosterStyle(cw.title)"
            >
              <div class="st-poster__scrim" />
              <span class="st-poster__play" aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>
              </span>
              <div class="st-poster__title">{{ cw.title }}</div>
              <div class="st-poster__prog">
                <span :style="{ width: Math.round((cw.position_seconds / cw.duration_seconds) * 100) + '%' }" />
              </div>
            </div>
            <div class="st-pmeta">
              <div class="st-pmeta__title">{{ cw.title }}</div>
              <div class="st-pmeta__sub t-mono" style="font-size: var(--text-xs); color: var(--text-tertiary)">
                {{ Math.round(Math.max(0, cw.duration_seconds - cw.position_seconds) / 60) }}m left
              </div>
            </div>
          </button>
        </div>
      </template>

      <!-- featured hero -->
      <div v-if="featured" style="margin-top: var(--space-8)">
        <StoryHero
          :item="featured"
          @play="emit('play', featured!)"
          @open="emit('navigate', { name: 'film', id: featured!.id })"
        />
      </div>

      <!-- new films -->
      <StorySection
        v-if="newFilms.length > 0"
        title="New films"
        @all="emit('navigate', { name: 'category', cat: 'All' })"
      >
        <StoryPoster
          v-for="f in newFilms"
          :key="f.id"
          :item="f"
          @click="f.status !== 'generating' && emit('navigate', { name: 'film', id: f.id })"
        />
      </StorySection>

      <!-- series -->
      <StorySection v-if="series.length > 0" title="Series">
        <StoryPoster
          v-for="s in series"
          :key="s.id"
          :item="s"
          @click="emit('navigate', { name: 'series', id: s.id })"
        />
      </StorySection>

      <!-- by category -->
      <template v-for="cat in catsWith" :key="cat.category">
        <StorySection
          :title="cat.category"
          accent
          @all="emit('navigate', { name: 'category', cat: cat.category })"
        >
          <StoryPoster
            v-for="x in allItems.filter((i) => i.category === cat.category && i.id !== featured?.id)"
            :key="x.id"
            :item="x"
            @click="x.status !== 'generating' && emit('navigate', { name: x.kind === 'series' ? 'series' : 'film', id: x.id })"
          />
        </StorySection>
      </template>

      <!-- empty state -->
      <div v-if="!featured && films.length === 0 && series.length === 0" class="st-empty">
        <p class="st-empty__title">No stories yet</p>
        <p class="t-serif t-secondary" style="font-size: var(--text-base); margin-top: var(--space-2)">
          Stories will be generated as your brain grows.
        </p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.st-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}
.st-page-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-xl);
  letter-spacing: -0.01em;
}
.ghost-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  height: 36px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-weight: 500;
  font-size: var(--text-sm);
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: border-color 0.12s, color 0.12s;
}
.ghost-btn:hover { border-color: var(--border-medium); color: var(--text-primary); }

.st-loading {
  font-family: var(--font-body);
  font-size: var(--text-base);
  color: var(--text-tertiary);
  padding: var(--space-10) 0;
  text-align: center;
}
.st-error {
  padding: var(--space-8);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  text-align: center;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}

.st-eyebrow {
  font-family: var(--font-body);
  font-weight: 500;
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.st-row {
  display: flex;
  gap: var(--space-4);
  overflow-x: auto;
  padding-bottom: var(--space-2);
  scroll-snap-type: x proximity;
}
.st-row::-webkit-scrollbar { height: 8px; }

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
.st-poster-card:hover { transform: translateY(-2px); }
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
.st-poster__title {
  position: absolute;
  left: 12px; right: 12px; bottom: 16px;
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
}
.st-poster__play {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%,-50%) scale(0.9);
  z-index: 2;
  width: 52px; height: 52px;
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
.st-pmeta__sub { font-size: var(--text-sm); color: var(--text-secondary); margin-top: 2px; }

.st-empty {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--background-surface);
  padding: var(--space-10);
  text-align: center;
  margin-top: var(--space-8);
}
.st-empty__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--text-md);
  color: var(--text-secondary);
}
</style>
