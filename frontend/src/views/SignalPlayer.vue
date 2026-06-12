<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, computed } from 'vue'
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
    <header class="page-header">
      <div class="header-left">
        <span class="page-tag">SECTION</span>
        <h1 class="page-title">SIGNAL // VIDEO CHANNEL</h1>
      </div>
      <div class="header-actions">
        <span class="header-count">{{ total }} TRANSMISSIONS</span>
      </div>
    </header>
    <div class="rule" />

    <div class="body">
      <div v-if="error" class="state-card state-card--error">{{ error }}</div>

      <div class="signal-layout">

        <!-- ── Library (left) ────────────────────────────────────────── -->
        <aside class="library">
          <div class="section-label">VIDEO LIBRARY</div>

          <div v-if="loading && videos.length === 0" class="library-skeleton">
            <div v-for="i in 4" :key="i" class="skeleton-card" />
          </div>

          <div v-else-if="videos.length === 0" class="library-empty">
            <p class="empty-text">NO TRANSMISSIONS YET</p>
            <p class="empty-hint">Videos appear here once the SIGNAL pipeline generates them.</p>
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
          >{{ loading ? 'LOADING…' : 'LOAD MORE' }}</button>
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
              <span v-if="selectedTopic" class="topic-tag">TOPIC: {{ selectedTopic }}</span>
            </div>

            <p v-if="selected.description" class="player-description">{{ selected.description }}</p>

            <div class="player-divider" />

            <div class="rating-row">
              <button
                class="btn btn--ghost rate-btn"
                :class="{ 'rate-btn--active': rated[selected.id] === 'like' }"
                @click="rate('like')"
              >▲ LIKE</button>
              <button
                class="btn btn--ghost rate-btn rate-btn--down"
                :class="{ 'rate-btn--active-down': rated[selected.id] === 'dislike' }"
                @click="rate('dislike')"
              >▼ DISLIKE</button>
              <span class="watch-readout">WATCHED: {{ (watchPct * 100).toFixed(0) }}%</span>
            </div>
          </template>

          <div v-else class="player-empty">
            <p class="empty-text">NO TRANSMISSION SELECTED</p>
            <p class="empty-hint">Select a ready video from the library.</p>
          </div>
        </section>
      </div>
    </div>

    <!-- ── Toast ─────────────────────────────────────────────────────── -->
    <Transition name="toast">
      <div v-if="toastVisible" class="toast">FEEDBACK LOGGED</div>
    </Transition>
  </div>
</template>

<style scoped>
/* ── Shell (mirrors HealthView conventions) ─────────────────────────────── */
.page { min-height: 100%; display: flex; flex-direction: column; }

.page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 28px 32px 24px;
}
.header-left { display: flex; align-items: baseline; gap: 16px; }
.page-tag {
  font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.14em;
  color: var(--text-muted); border: 1px solid var(--border); padding: 2px 6px;
}
.page-title {
  font-family: var(--font-mono); font-size: 18px; letter-spacing: 0.07em;
  color: var(--text-primary);
}
.header-count {
  font-family: var(--font-mono); font-size: 10px;
  color: var(--text-muted); letter-spacing: 0.12em;
}
.rule { height: 1px; background: var(--border); }

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
  font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.12em;
  color: var(--text-secondary); padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
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
  border: 1px solid var(--border);
  background: repeating-linear-gradient(90deg, #12121a 0px, #1e1e2e 40px, #12121a 80px);
  background-size: 200% 100%;
  animation: scan 1.5s infinite linear;
}
@keyframes scan { 0% { background-position: 0% 0; } 100% { background-position: -200% 0; } }

.library-empty, .player-empty {
  border: 1px solid var(--border); background: var(--surface);
  padding: 28px 20px; display: flex; flex-direction: column; gap: 8px;
  align-items: center; text-align: center;
}
.empty-text {
  font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.18em;
  color: var(--text-2);
}
.empty-hint { font-family: var(--font-sans); font-size: 11px; color: var(--text-muted); }

.load-more { width: 100%; }

/* ── Player panel ───────────────────────────────────────────────────────── */
.player-panel {
  display: flex; flex-direction: column; gap: 14px;
  border: 1px solid var(--border); background: var(--surface);
  padding: 20px;
  min-width: 0;
}

.player-frame {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  border: 1px solid var(--border);
}
.player-video { width: 100%; height: 100%; display: block; }

.player-title {
  font-family: var(--font-mono); font-size: 15px; font-weight: 600;
  letter-spacing: 0.04em; color: var(--text-1); line-height: 1.4;
}

.player-meta {
  display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
}

.topic-tag {
  font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.12em;
  color: var(--accent); border: 1px solid var(--accent); padding: 2px 8px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;
}

.player-description {
  font-family: var(--font-sans); font-size: 13px; line-height: 1.65;
  color: var(--text-2);
}

.player-divider { height: 1px; background: var(--border); }

/* ── Rating ─────────────────────────────────────────────────────────────── */
.rating-row { display: flex; align-items: center; gap: 10px; }

.btn {
  font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.14em;
  border: 1px solid var(--border); padding: 6px 14px; cursor: pointer;
  background: transparent; color: var(--text-2); border-radius: 0;
  transition: border-color 0.12s, color 0.12s, background 0.12s;
}
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn--ghost:hover:not(:disabled) { border-color: var(--accent); color: var(--text-1); }

.rate-btn--active {
  border-color: var(--status-active); color: var(--status-active);
}
.rate-btn--active-down {
  border-color: var(--status-error); color: var(--status-error);
}

.watch-readout {
  margin-left: auto;
  font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.12em;
  color: var(--text-muted);
}

/* ── Error card ─────────────────────────────────────────────────────────── */
.state-card {
  border: 1px solid var(--border); padding: 16px 20px; background: var(--surface);
}
.state-card--error {
  border-color: var(--status-error); color: var(--status-error);
  font-family: var(--font-mono); font-size: 11px;
}

/* ── Toast ──────────────────────────────────────────────────────────────── */
.toast {
  position: fixed;
  right: 24px; bottom: 24px;
  font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.16em;
  color: var(--text-1); background: var(--elevated);
  border: 1px solid var(--accent);
  padding: 10px 16px;
  z-index: 100;
}
.toast-enter-active, .toast-leave-active { transition: opacity 0.18s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; }

@media (prefers-reduced-motion: reduce) { .skeleton-card { animation: none; } }
</style>
