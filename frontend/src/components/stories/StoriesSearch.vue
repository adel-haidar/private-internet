<script setup lang="ts">
/**
 * StoriesSearch — Search / category discovery.
 * Uses GET /api/stories/search?q= from the real backend.
 * Genre grid replaced with live categories from the library.
 */
import { computed, ref, watch, onMounted } from 'vue'
import type { StoriesView, StoryItem } from '../../composables/useStories'
import { useStories, searchStories, stDurLabel } from '../../composables/useStories'

const emit = defineEmits<{
  (e: 'navigate', v: StoriesView): void
}>()

const { categories, loadLibrary } = useStories()

onMounted(() => loadLibrary())

const q = ref('')
const results = ref<{ films: StoryItem[]; series: StoryItem[] }>({ films: [], series: [] })
const searching = ref(false)
const searchError = ref<string | null>(null)

// Debounced search
let debounceTimer: ReturnType<typeof setTimeout> | null = null

watch(q, (val) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  const trimmed = val.trim()
  if (!trimmed) {
    results.value = { films: [], series: [] }
    searchError.value = null
    return
  }
  debounceTimer = setTimeout(() => doSearch(trimmed), 350)
})

async function doSearch(query: string) {
  searching.value = true
  searchError.value = null
  try {
    results.value = await searchStories(query)
  } catch (e) {
    searchError.value = e instanceof Error ? e.message : String(e)
    results.value = { films: [], series: [] }
  } finally {
    searching.value = false
  }
}

const flatResults = computed<StoryItem[]>(() => [...results.value.films, ...results.value.series])
const hasQuery = computed(() => q.value.trim().length > 0)
const isEmpty = computed(() => hasQuery.value && !searching.value && flatResults.value.length === 0)
</script>

<template>
  <div style="max-width: var(--content-reading); margin: 0 auto">
    <!-- search bar -->
    <div class="search-row">
      <div class="search-input-wrap">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="search-icon"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.3-4.3"/></svg>
        <input
          v-model="q"
          class="search-input"
          placeholder="Search films, series, topics…"
          autofocus
        />
      </div>
      <button class="cancel-btn" @click="emit('navigate', { name: 'library' })">Cancel</button>
    </div>

    <!-- before typing: categories -->
    <template v-if="!hasQuery">
      <div v-if="categories.length > 0">
        <div class="st-eyebrow" style="margin-bottom: var(--space-3)">Categories</div>
        <div class="st-genres">
          <button
            v-for="c in categories"
            :key="c.category"
            class="genre-tile"
            @click="emit('navigate', { name: 'category', cat: c.category })"
          >
            <span>{{ c.category }}</span>
            <span class="genre-tile__count">{{ c.film_count + c.series_count }}</span>
          </button>
        </div>
      </div>
    </template>

    <!-- searching indicator -->
    <div v-else-if="searching" class="st-searching">Searching…</div>

    <!-- error -->
    <div v-else-if="searchError" class="empty-state">
      <p class="empty-title">Search failed</p>
      <p class="t-serif t-secondary" style="font-size: var(--text-base); margin-top: var(--space-2)">{{ searchError }}</p>
    </div>

    <!-- no results -->
    <template v-else-if="isEmpty">
      <div class="empty-state">
        <p class="empty-title">Nothing found for "{{ q }}"</p>
        <p class="t-serif t-secondary" style="font-size: var(--text-base); margin-top: var(--space-2)">Try a topic from your brain.</p>
      </div>
    </template>

    <!-- results -->
    <template v-else-if="flatResults.length > 0">
      <div style="display: flex; flex-direction: column">
        <button
          v-for="x in flatResults"
          :key="x.id"
          class="result-row"
          @click="emit('navigate', { name: x.kind === 'series' ? 'series' : 'film', id: x.id })"
        >
          <span
            class="result-thumb"
            :style="x.thumbnail_url
              ? { backgroundImage: `url(${x.thumbnail_url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
              : undefined"
          />
          <div style="flex: 1; min-width: 0; text-align: left">
            <div style="font-family: var(--font-display); font-weight: 500; font-size: var(--text-base)">{{ x.title }}</div>
            <div class="t-mono t-tertiary" style="font-size: var(--text-xs); margin-top: 2px">
              {{ x.kind === 'series'
                ? `Series · ${x.episode_count ?? '?'} episodes`
                : (x.category ? `${x.category} · ` : '') + (x.duration_seconds ? stDurLabel(x.duration_seconds) : '') }}
            </div>
          </div>
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.search-row {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  margin-bottom: var(--space-6);
}
.search-input-wrap {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}
.search-icon {
  position: absolute;
  left: var(--space-3);
  color: var(--text-tertiary);
  pointer-events: none;
}
.search-input {
  width: 100%;
  height: 40px;
  padding: 0 var(--space-4) 0 36px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--background-input);
  color: var(--text-primary);
  font-family: var(--font-body);
  font-size: var(--text-base);
  outline: none;
  transition: border-color 0.12s;
}
.search-input:focus { border-color: var(--accent-primary); }
.cancel-btn {
  height: 40px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-weight: 500;
  font-size: var(--text-sm);
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
}
.cancel-btn:hover { border-color: var(--border-medium); color: var(--text-primary); }

.st-eyebrow {
  font-family: var(--font-body);
  font-weight: 500;
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.st-searching {
  font-family: var(--font-body);
  font-size: var(--text-base);
  color: var(--text-tertiary);
  padding: var(--space-6) 0;
  text-align: center;
}

.st-genres {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--space-3);
}
.genre-tile {
  height: 52px;
  border-radius: var(--radius-md);
  background: var(--background-surface);
  border: 1px solid var(--border-subtle);
  font-family: var(--font-display);
  font-weight: 500;
  font-size: var(--text-base);
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-4);
  cursor: pointer;
  transition: border-color 0.12s;
}
.genre-tile:hover { border-color: var(--border-medium); }
.genre-tile__count {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.result-row {
  display: flex;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-2);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--background-surface);
  cursor: pointer;
  transition: border-color 0.12s;
}
.result-row:hover { border-color: var(--border-medium); }
.result-thumb {
  width: 48px;
  height: 72px;
  border-radius: var(--radius-sm);
  flex: 0 0 auto;
  display: block;
  background: var(--background-raised);
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
</style>
