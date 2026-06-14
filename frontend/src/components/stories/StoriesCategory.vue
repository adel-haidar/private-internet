<script setup lang="ts">
/**
 * StoriesCategory — 3-col poster grid with inline Sort + Type filters.
 * Uses live library data from useStories().
 */
import { computed, ref, onMounted } from 'vue'
import type { StoriesView } from '../../composables/useStories'
import { useStories } from '../../composables/useStories'
import StoryPoster from './StoryPoster.vue'

const props = defineProps<{
  cat: string
}>()

const emit = defineEmits<{
  (e: 'navigate', v: StoriesView): void
}>()

const { films, series, loadLibrary, libraryLoading } = useStories()

onMounted(() => loadLibrary())

const sort = ref('Recent')
const type = ref('All')

const allItems = computed(() => [...films.value, ...series.value])

const items = computed(() => {
  let list = allItems.value.filter(
    (x) => x.status !== 'generating' && (props.cat === 'All' || x.category === props.cat),
  )
  if (type.value === 'Films') list = list.filter((x) => x.kind === 'film')
  if (type.value === 'Series') list = list.filter((x) => x.kind === 'series')
  if (sort.value === 'Recent') {
    list = [...list].sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''))
  } else if (sort.value === 'Longest') {
    list = [...list].sort((a, b) => (b.duration_seconds ?? 0) - (a.duration_seconds ?? 0))
  }
  return list
})

const filmCount = computed(() => items.value.filter((x) => x.kind === 'film').length)
const seriesCount = computed(() => items.value.filter((x) => x.kind === 'series').length)

const title = computed(() => (props.cat === 'All' ? 'All films & series' : props.cat))
</script>

<template>
  <div>
    <button class="back-btn" @click="emit('navigate', { name: 'library' })">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="transform: rotate(180deg)"><path d="M9 18l6-6-6-6"/></svg>
      Stories
    </button>

    <div style="margin-bottom: var(--space-6)">
      <h1 class="cat-title">{{ title }}</h1>
      <div class="t-mono t-secondary" style="font-size: var(--text-sm); margin-top: var(--space-2)">
        {{ filmCount }} films · {{ seriesCount }} series
      </div>
    </div>

    <!-- loading -->
    <div v-if="libraryLoading" class="st-loading">Loading…</div>

    <template v-else>
      <!-- inline filters -->
      <div class="filters">
        <div class="filter-group">
          <span class="filter-label">Sort:</span>
          <button
            v-for="opt in ['Recent', 'Longest']"
            :key="opt"
            class="filter-pill"
            :class="{ 'filter-pill--active': sort === opt }"
            @click="sort = opt"
          >{{ opt }}</button>
        </div>
        <div class="filter-group">
          <span class="filter-label">Type:</span>
          <button
            v-for="opt in ['All', 'Films', 'Series']"
            :key="opt"
            class="filter-pill"
            :class="{ 'filter-pill--active': type === opt }"
            @click="type = opt"
          >{{ opt }}</button>
        </div>
      </div>

      <!-- empty state -->
      <div v-if="items.length === 0" class="empty-state">
        <p class="empty-title">No {{ cat !== 'All' ? cat.toLowerCase() : '' }} stories yet</p>
        <p class="t-serif t-secondary" style="font-size: var(--text-base); margin-top: var(--space-2)">
          More content will be generated as your brain grows.
        </p>
      </div>

      <!-- poster grid -->
      <div v-else class="st-grid">
        <StoryPoster
          v-for="x in items"
          :key="x.id"
          :item="x"
          @click="emit('navigate', { name: x.kind === 'series' ? 'series' : 'film', id: x.id })"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.st-loading {
  font-family: var(--font-body);
  font-size: var(--text-base);
  color: var(--text-tertiary);
  padding: var(--space-10) 0;
  text-align: center;
}
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  height: 32px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-family: var(--font-display);
  font-weight: 500;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  margin-bottom: var(--space-4);
}
.back-btn:hover { border-color: var(--border-medium); color: var(--text-primary); }

.cat-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-xl);
  letter-spacing: -0.01em;
}

.filters {
  display: flex;
  gap: var(--space-6);
  margin-bottom: var(--space-6);
  flex-wrap: wrap;
}
.filter-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.filter-label {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  font-family: var(--font-body);
}
.filter-pill {
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: var(--text-sm);
  font-family: var(--font-display);
  font-weight: 500;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.12s;
}
.filter-pill:hover { border-color: var(--border-medium); color: var(--text-primary); }
.filter-pill--active {
  background: var(--accent-surface);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.empty-state {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--background-surface);
  padding: var(--space-10);
  text-align: center;
}
.empty-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--text-md);
  color: var(--text-secondary);
}

.st-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--space-5);
}
</style>
