<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, computed } from 'vue'
import PageHead from '../components/ui/PageHead.vue'
import { useSignalLibrary, logInteraction, type Video } from '../composables/useContent'
import VideoCard from '../components/VideoCard.vue'
import CreatorBadge from '../components/CreatorBadge.vue'

const {
  videos, selected, total, loading, error,
  topicNames, creators, hasMore, loadMore, select,
} = useSignalLibrary()

// ── Player + watch tracking (core RL signal) ────────────────────────────────

const videoEl = ref<HTMLVideoElement | null>(null)
const currentTime = ref(0)
const duration = ref(0)
let endedLogged = false

const watchPct = computed(() =>
  duration.value > 0 ? currentTime.value / duration.value : 0)

function onTimeUpdate(): void {
  if (!videoEl.value) return
  currentTime.value = videoEl.value.currentTime
  duration.value = videoEl.value.duration || 0
}

async function onVideoEnded(): Promise<void> {
  if (!selected.value || endedLogged) return
  endedLogged = true
  await logInteraction(selected.value.id, 'video', 'watch_complete', 1.0).catch(() => {})
}

/** Flush the watch signal for the video being left (switch or unmount). */
function flushWatch(v: Video | null): void {
  if (!v) return
  const pct = watchPct.value
  if (!endedLogged) {
    if (pct > 0.1 && pct < 1.0) {
      void logInteraction(v.id, 'video', 'watch_partial', pct).catch(() => {})
    } else if (pct <= 0.1) {
      void logInteraction(v.id, 'video', 'skip').catch(() => {})
    }
  }
  currentTime.value = 0
  duration.value = 0
  endedLogged = false
}

function selectVideo(v: Video): void {
  if (selected.value?.id === v.id) return
  flushWatch(selected.value)
  select(v)
}

onBeforeUnmount(() => flushWatch(selected.value))

// ── Like / dislike + toast ───────────────────────────────────────────────────

const toastVisible = ref(false)
const rated = ref<Record<string, 'like' | 'dislike'>>({})
let toastTimer: ReturnType<typeof setTimeout> | null = null

async function rate(action: 'like' | 'dislike'): Promise<void> {
  if (!selected.value) return
  const id = selected.value.id
  rated.value = { ...rated.value, [id]: action }  // optimistic
  toastVisible.value = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastVisible.value = false }, 1500)
  await logInteraction(id, 'video', action).catch(() => {})
}

// ── Display helpers ──────────────────────────────────────────────────────────

const selectedCreator = computed(() =>
  selected.value ? creators.value[selected.value.creator_id] : undefined)

const selectedTopic = computed(() =>
  selected.value ? topicNames.value[selected.value.topic_id] : undefined)

onMounted(() => { void loadMore() })
</script>

<template>
  <div class="page">

    <!-- ── Header ──────────────────────────────────────────────────────── -->
    <PageHead title="Signal" :desc="total ? `${total} video${total === 1 ? '' : 's'} in the library` : 'AI-generated video channel'" />

    <div class="body">
      <div v-if="error" class="state-card state-card--error">{{ error }}</div>

      <div class="signal-layout">

        <!-- ── Library (left) ────────────────────────────────────────── -->
        <aside class="library">
          <div class="section-label">Video library</div>

          <div v-if="loading && videos.length === 0" class="library-skeleton">
            <div v-for="i in 4" :key="i" class="skeleton-card" />
          </div>

          <div v-else-if="videos.length === 0" class="library-empty">
            <p class="empty-text">No videos yet</p>
            <p class="empty-hint">Videos appear here once the Signal pipeline generates them.</p>
          </div>

          <div v-else class="library-list">
            <VideoCard
              v-for="v in videos"
              :key="v.id"
              :video="v"
              :active="selected?.id === v.id"
              @select="selectVideo"
            />
          </div>

          <button
            v-if="hasMore()"
            class="btn btn--ghost load-more"
            :disabled="loading"
            @click="loadMore"
          >{{ loading ? 'Loading…' : 'Load more' }}</button>
        </aside>

        <!-- ── Player (right) ────────────────────────────────────────── -->
        <section class="player-panel">
          <template v-if="selected">
            <div class="player-frame">
              <video
                ref="videoEl"
                :key="selected.id"
                :src="selected.video_url ?? undefined"
                :poster="selected.thumbnail_url ?? undefined"
                controls
                preload="metadata"
                class="player-video"
                @timeupdate="onTimeUpdate"
                @ended="onVideoEnded"
              />
            </div>

            <h2 class="player-title">{{ selected.title }}</h2>

            <div class="player-meta">
              <CreatorBadge
                :name="selected.creator_name"
                :slug="selectedCreator?.slug"
                :avatar-url="selectedCreator?.avatar_url ?? selected.creator_avatar"
                :score="selectedCreator?.score ?? selected.score"
                :bio="selectedCreator?.bio ?? undefined"
              />
              <span v-if="selectedTopic" class="topic-tag">{{ selectedTopic }}</span>
            </div>

            <p v-if="selected.description" class="player-description">{{ selected.description }}</p>

            <div class="player-divider" />

            <div class="rating-row">
              <button
                class="btn btn--ghost rate-btn"
                :class="{ 'rate-btn--active': rated[selected.id] === 'like' }"
                @click="rate('like')"
              >▲ Like</button>
              <button
                class="btn btn--ghost rate-btn rate-btn--down"
                :class="{ 'rate-btn--active-down': rated[selected.id] === 'dislike' }"
                @click="rate('dislike')"
              >▼ Dislike</button>
              <span class="watch-readout">Watched: {{ (watchPct * 100).toFixed(0) }}%</span>
            </div>
          </template>

          <div v-else class="player-empty">
            <p class="empty-text">No video selected</p>
            <p class="empty-hint">Select a ready video from the library.</p>
          </div>
        </section>
      </div>
    </div>

    <!-- ── Toast ─────────────────────────────────────────────────────── -->
    <Transition name="toast">
      <div v-if="toastVisible" class="toast">Feedback logged</div>
    </Transition>
  </div>
</template>

<style scoped>
/* ── Shell ──────────────────────────────────────────────────────────────── */
.page { min-height: 100%; display: flex; flex-direction: column; }

.body { padding: 28px 32px 48px; display: flex; flex-direction: column; gap: 20px; flex: 1; }

/* ── Two-panel layout ───────────────────────────────────────────────────── */
.signal-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
  align-items: start;
}
@media (max-width: 1000px) { .signal-layout { grid-template-columns: 1fr; } }

/* ── Library ────────────────────────────────────────────────────────────── */
.library { display: flex; flex-direction: column; gap: 12px; min-width: 0; }

.section-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-subtle);
}

.library-list {
  display: flex; flex-direction: column; gap: 12px;
  max-height: calc(100vh - 240px);
  overflow-y: auto;
  padding-right: 2px;
}
@media (max-width: 1000px) { .library-list { max-height: none; } }

.library-skeleton { display: flex; flex-direction: column; gap: 12px; }
.skeleton-card {
  height: 120px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm, 8px);
  background: var(--background-raised);
  position: relative;
  overflow: hidden;
}
.skeleton-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, var(--background-surface) 50%, transparent 100%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}
@keyframes shimmer { from { background-position: -200% 0; } to { background-position: 200% 0; } }

.library-empty, .player-empty {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 12px);
  background: var(--background-surface);
  padding: 28px 20px; display: flex; flex-direction: column; gap: 8px;
  align-items: center; text-align: center;
}
.empty-text { font-size: 15px; font-weight: 500; color: var(--text-secondary); }
.empty-hint { font-size: 13px; color: var(--text-tertiary); }

.load-more { width: 100%; }

/* ── Player panel ───────────────────────────────────────────────────────── */
.player-panel {
  display: flex; flex-direction: column; gap: 14px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 12px);
  background: var(--background-surface);
  padding: 20px;
  min-width: 0;
}

.player-frame {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  border-radius: var(--radius-sm, 8px);
  overflow: hidden;
}
.player-video { width: 100%; height: 100%; display: block; }

.player-title {
  font-size: 16px; font-weight: 600;
  color: var(--text-primary); line-height: 1.4;
}

.player-meta {
  display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
}

.topic-tag {
  font-size: 12px;
  color: var(--brain-amber);
  border: 1px solid var(--brain-amber);
  border-radius: var(--radius-pill, 999px);
  padding: 2px 10px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;
}

.player-description {
  font-size: 14px; line-height: 1.65;
  color: var(--text-secondary);
}

.player-divider { height: 1px; background: var(--border-subtle); }

/* ── Rating ─────────────────────────────────────────────────────────────── */
.rating-row { display: flex; align-items: center; gap: 10px; }

.btn {
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill, 999px);
  padding: 6px 16px;
  cursor: pointer;
  background: transparent;
  color: var(--text-secondary);
  transition: border-color 0.15s, color 0.15s;
}
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn--ghost:hover:not(:disabled) { border-color: var(--border-medium); color: var(--text-primary); }

.rate-btn--active {
  border-color: var(--success); color: var(--success); background: var(--success-surface);
}
.rate-btn--active-down {
  border-color: var(--danger); color: var(--danger); background: var(--danger-surface);
}

.watch-readout {
  margin-left: auto;
  font-family: var(--font-mono); font-size: 12px;
  color: var(--text-tertiary);
}

/* ── Error card ─────────────────────────────────────────────────────────── */
.state-card {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm, 8px);
  padding: 16px 20px;
  background: var(--background-surface);
}
.state-card--error {
  border-color: var(--danger); color: var(--danger);
  background: var(--danger-surface);
  font-size: 13px;
}

/* ── Toast ──────────────────────────────────────────────────────────────── */
.toast {
  position: fixed;
  right: 24px; bottom: 24px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--background-raised);
  border: 1px solid var(--accent-primary);
  border-radius: var(--radius-sm, 8px);
  padding: 10px 16px;
  z-index: 100;
}
.toast-enter-active, .toast-leave-active { transition: opacity 0.18s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; }

@media (prefers-reduced-motion: reduce) { .skeleton-card::after { animation: none; } }
</style>
