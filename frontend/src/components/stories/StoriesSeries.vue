<script setup lang="ts">
/**
 * StoriesSeries — Series "box set" page.
 * Fetches series detail + episodes from /api/stories/series/{id}
 * and /api/stories/series/{id}/episodes.
 */
import { computed, ref, onMounted, watch } from 'vue'
import type { StoriesView, StoryItem } from '../../composables/useStories'
import {
  fetchSeries,
  fetchEpisodes,
  stPosterStyle,
  stDurLabel,
  postLike,
  type StoryEpisode,
} from '../../composables/useStories'

const props = defineProps<{
  id: string
}>()

const emit = defineEmits<{
  (e: 'navigate', v: StoriesView): void
  (e: 'play', item: StoryItem, ep?: number): void
}>()

const series = ref<StoryItem | null>(null)
const episodes = ref<StoryEpisode[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const saved = ref(false)
const liked = ref(false)

async function load() {
  loading.value = true
  error.value = null
  try {
    const [seriesData, epsData] = await Promise.all([
      fetchSeries(props.id),
      fetchEpisodes(props.id),
    ])
    series.value = seriesData
    episodes.value = epsData
    liked.value = seriesData.liked ?? false
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.id, load)

/** First episode with partial progress, or null. */
const resumeEp = computed(() =>
  episodes.value.find((e) => e.position_seconds != null && !e.completed) ?? null
)

/** Episode count from the series detail or actual episodes list. */
const epCount = computed(() => series.value?.episode_count ?? episodes.value.length)

/** Unique seasons present in episodes. */
const seasons = computed(() => {
  const s = new Set(episodes.value.map((e) => e.season_number))
  return [...s].sort()
})

const activeSeason = ref(1)

const visibleEps = computed(() =>
  episodes.value.filter((e) => e.season_number === activeSeason.value)
)

function playEpisode(ep: StoryEpisode) {
  if (!series.value) return
  emit('play', series.value, ep.episode_number)
}

function progressPct(ep: StoryEpisode): number | null {
  if (ep.position_seconds == null || !ep.duration_seconds) return null
  return Math.min(100, Math.round((ep.position_seconds / ep.duration_seconds) * 100))
}

async function toggleLike() {
  if (!series.value) return
  const next = !liked.value
  liked.value = next
  try {
    await postLike({ content_type: 'series', content_id: series.value.id, liked: next })
  } catch {
    liked.value = !next
  }
}
</script>

<template>
  <!-- loading -->
  <div v-if="loading" class="st-loading">Loading…</div>

  <!-- error -->
  <div v-else-if="error" class="st-error">
    <p>{{ error }}</p>
    <button class="back-btn" @click="load()">Retry</button>
  </div>

  <div v-else-if="series">
    <!-- back -->
    <button class="back-btn" @click="emit('navigate', { name: 'library' })">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="transform: rotate(180deg)"><path d="M9 18l6-6-6-6"/></svg>
      Back to Stories
    </button>

    <!-- hero banner -->
    <div
      class="st-series-hero"
      :style="series.poster_url || series.thumbnail_url
        ? { backgroundImage: `url(${series.poster_url ?? series.thumbnail_url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
        : stPosterStyle(series.title)"
    >
      <div class="st-cine" />
      <div class="st-series-hero__body">
        <div class="st-series-hero__title">{{ series.title }}</div>
        <div class="t-mono" style="font-size: var(--text-xs); color: rgba(255,255,255,0.6); margin-top: var(--space-3)">
          SERIES · {{ epCount }} Episodes
        </div>
      </div>
    </div>

    <!-- action row -->
    <div class="series-actions">
      <button
        class="play-cta"
        :class="{ 'play-cta--amber': !!resumeEp }"
        :disabled="series.status !== 'ready'"
        @click="series && emit('play', series, resumeEp ? resumeEp.episode_number : 1)"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>
        {{ resumeEp ? `Continue E${resumeEp.episode_number} · ${Math.round(Math.max(0, (resumeEp.duration_seconds ?? 0) - (resumeEp.position_seconds ?? 0)) / 60)}m left` : 'Play from start' }}
      </button>
      <button class="secondary-btn" @click="saved = !saved">
        <svg v-if="saved" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6L9 17l-5-5"/></svg>
        <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
        {{ saved ? 'Saved' : 'Save series' }}
      </button>
      <button class="secondary-btn like-btn" :class="{ 'like-btn--on': liked }" @click="toggleLike">
        <svg width="16" height="16" viewBox="0 0 24 24" :fill="liked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8"><path d="M20.8 5.6a5.5 5.5 0 0 0-7.8 0L12 6.6l-1-1a5.5 5.5 0 1 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>
        {{ liked ? 'Liked' : 'Like' }}
      </button>
    </div>

    <div style="max-width: var(--content-reading)">
      <p v-if="series.premise" class="t-serif" style="font-size: var(--text-md); line-height: 1.75; margin-bottom: var(--space-6)">
        {{ series.premise }}
      </p>

      <!-- Season selector -->
      <div v-if="seasons.length > 1" class="st-seasons" style="margin-bottom: var(--space-5)">
        <button
          v-for="s in seasons"
          :key="s"
          class="st-season"
          :class="{ 'st-season--active': activeSeason === s }"
          @click="activeSeason = s"
        >Season {{ s }}</button>
      </div>

      <!-- Episode list -->
      <div v-if="visibleEps.length > 0" class="ep-list">
        <div
          v-for="ep in visibleEps"
          :key="ep.id"
          class="ep-row"
          :class="{ 'ep-row--active': ep.position_seconds != null && !ep.completed }"
          @click="playEpisode(ep)"
        >
          <!-- 16:9 thumbnail -->
          <div
            class="ep-thumb"
            :style="ep.thumbnail_url
              ? { backgroundImage: `url(${ep.thumbnail_url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
              : stPosterStyle(series.title + ep.episode_number)"
          >
            <span v-if="ep.duration_seconds" class="ep-thumb__dur">{{ stDurLabel(ep.duration_seconds) }}</span>
            <span class="ep-thumb__play" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>
            </span>
          </div>
          <div class="ep-body">
            <div class="ep-header">
              <!-- watched checkmark or episode number -->
              <span v-if="ep.completed" class="ep-check" aria-label="Watched">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6L9 17l-5-5"/></svg>
              </span>
              <span v-else class="t-mono t-tertiary" style="font-size: var(--text-sm)">E{{ ep.episode_number }}</span>
              <span class="ep-title">{{ ep.title }}</span>
            </div>
            <p v-if="ep.premise" class="t-secondary" style="font-size: var(--text-sm); margin-top: 4px">{{ ep.premise }}</p>
            <div class="ep-footer">
              <span v-if="ep.duration_seconds" class="t-mono t-tertiary" style="font-size: var(--text-xs)">{{ stDurLabel(ep.duration_seconds) }}</span>
              <div v-if="progressPct(ep) != null" class="ep-progress">
                <div class="ep-progress__fill" :style="{ width: progressPct(ep) + '%' }" />
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="st-no-eps">No episodes available yet.</div>
    </div>
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

.st-series-hero {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  aspect-ratio: 21/8;
  background: var(--background-raised);
  margin-bottom: var(--space-6);
}
.st-cine {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(12,12,20,0.92) 0%, rgba(12,12,20,0.60) 40%, rgba(12,12,20,0) 100%);
}
.st-series-hero__body {
  position: absolute;
  left: var(--space-8);
  right: var(--space-8);
  bottom: var(--space-6);
}
.st-series-hero__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--text-xl);
  color: #fff;
  line-height: 1.1;
}

.series-actions {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
  flex-wrap: wrap;
}
.play-cta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 40px;
  padding: 0 var(--space-5);
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--text-sm);
  background: var(--accent-primary);
  color: #fff;
  border: none;
  cursor: pointer;
  transition: background 0.12s;
}
.play-cta:hover:not(:disabled) { background: var(--accent-hover); }
.play-cta:disabled { opacity: 0.5; cursor: not-allowed; }
.play-cta--amber { background: var(--brain-amber); color: #1c1b2e; }
.play-cta--amber:hover:not(:disabled) { opacity: 0.9; }
.secondary-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
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
  transition: border-color 0.12s, color 0.12s;
}
.secondary-btn:hover { border-color: var(--border-medium); color: var(--text-primary); }
.like-btn--on { color: var(--brain-amber); border-color: var(--brain-amber); }

.st-seasons { display: flex; gap: var(--space-2); }
.st-season {
  height: 32px;
  padding: 0 16px;
  border-radius: 999px;
  font-family: var(--font-display);
  font-weight: 500;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  background: var(--background-raised);
  border: 1px solid transparent;
  cursor: pointer;
}
.st-season--active {
  background: var(--brain-amber-surface);
  color: var(--brain-amber);
  border-color: var(--brain-amber);
}

.ep-list { display: flex; flex-direction: column; }
.ep-row {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4) 0;
  border-top: 1px solid var(--border-subtle);
  cursor: pointer;
  align-items: flex-start;
  transition: background 0.1s;
}
.ep-row:first-child { border-top: none; }
.ep-row:hover { background: var(--background-raised); border-radius: var(--radius-sm); }
.ep-row--active {
  border-left: 3px solid var(--accent-primary);
  padding-left: var(--space-4);
  margin-left: calc(var(--space-4) * -1);
  border-radius: 2px;
}

.ep-thumb {
  width: 132px;
  height: 76px;
  border-radius: var(--radius-sm);
  flex: 0 0 auto;
  position: relative;
  overflow: hidden;
  background: var(--background-raised);
}
.ep-thumb__dur {
  position: absolute;
  bottom: 5px; right: 5px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(0,0,0,0.72);
  color: #fff;
  font-family: var(--font-mono);
  font-size: 10px;
  z-index: 2;
}
.ep-thumb__play {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #fff;
  opacity: 0;
  background: rgba(0,0,0,0.3);
  transition: opacity 0.15s;
}
.ep-row:hover .ep-thumb__play { opacity: 1; }

.ep-body { flex: 1; min-width: 0; }
.ep-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.ep-check { color: var(--success); display: flex; }
.ep-title {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: var(--text-md);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ep-footer {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-2);
}
.ep-progress {
  width: 160px;
  height: 4px;
  background: var(--background-raised);
  border-radius: 999px;
  overflow: hidden;
}
.ep-progress__fill {
  height: 100%;
  background: var(--brain-amber);
  border-radius: 999px;
}

.st-no-eps {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  padding: var(--space-6) 0;
}
</style>
