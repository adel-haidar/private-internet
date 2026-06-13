<script setup lang="ts">
import { onMounted, ref } from 'vue'
import PostCard from '../components/PostCard.vue'
import PageHead from '../components/ui/PageHead.vue'
import { usePulseFeed, type PostSort } from '../composables/useContent'
import { requireAuth } from '../composables/useAuth'

const { posts, total, sort, loading, error, hasMore, loadMore, setSort } = usePulseFeed()

const SORTS: Array<{ id: PostSort; label: string }> = [
  { id: 'latest', label: 'LATEST' },
  { id: 'top', label: 'TOP' },
  { id: 'unrated', label: 'UNRATED' },
]

// topic_id → name map for the TOPIC line on each card
const topicNames = ref<Record<string, string>>({})

async function loadTopics() {
  try {
    const token = await requireAuth()
    const base = import.meta.env.DEV ? '' : 'https://adel-intelligence.com'
    const res = await fetch(`${base}/api/content/topics?page=1&page_size=200`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) return
    const data = await res.json()
    const map: Record<string, string> = {}
    for (const t of data.items ?? []) map[t.id] = t.name
    topicNames.value = map
  } catch {
    /* topic line is optional decoration — never block the feed */
  }
}

// bottom-right toast, 1.5s
const toast = ref<string | null>(null)
let toastTimer: ReturnType<typeof setTimeout> | undefined
function showToast(message: string) {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = null), 1500)
}

onMounted(() => {
  loadMore()
  loadTopics()
})
</script>

<template>
  <div class="pulse">
    <div class="pulse-head">
      <div class="title-row">
        <PageHead title="Pulse" :desc="total ? `${total} dispatches` : 'AI content feed'" />
      </div>
      <div class="sort-row">
        <span class="sort-label">Sort:</span>
        <button
          v-for="s in SORTS"
          :key="s.id"
          class="sort-tab"
          :class="{ active: sort === s.id }"
          @click="setSort(s.id)"
        >{{ s.label.charAt(0) + s.label.slice(1).toLowerCase() }}</button>
      </div>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="feed">
      <PostCard
        v-for="post in posts"
        :key="post.id"
        :post="post"
        :topic-name="topicNames[post.topic_id]"
        @feedback="showToast"
      />

      <template v-if="loading">
        <div v-for="i in 3" :key="'skeleton-' + i" class="skeleton">
          <div class="skeleton-line mono">████████ ███████ ████</div>
          <div class="skeleton-line mono">██████████████ ██████████ ████████</div>
          <div class="skeleton-line mono">███████ █████</div>
        </div>
      </template>

      <div v-if="!loading && posts.length === 0 && !error" class="empty">
        No posts yet — run the post generation job.
      </div>
    </div>

    <button
      v-if="hasMore() && posts.length > 0"
      class="load-more"
      :disabled="loading"
      @click="loadMore"
    >{{ loading ? 'Loading…' : 'Load more' }}</button>

    <Transition name="toast">
      <div v-if="toast" class="toast mono">{{ toast }}</div>
    </Transition>
  </div>
</template>

<style scoped>
.pulse {
  max-width: 680px;
  margin: 0 auto;
  padding: var(--gutter, 24px);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.pulse-head {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 12px);
  background: var(--background-surface);
  overflow: hidden;
}
.title-row {
  padding: 0;
}
.sort-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  font-size: 13px;
  border-top: 1px solid var(--border-subtle);
}
.sort-label { color: var(--text-tertiary); margin-right: 6px; }
.sort-tab {
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-pill, 999px);
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 13px;
  padding: 3px 10px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.sort-tab:hover { color: var(--text-primary); border-color: var(--border-subtle); }
.sort-tab.active { color: var(--accent-primary); border-color: var(--accent-primary); background: var(--accent-surface); }

.feed {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.error {
  border: 1px solid var(--danger);
  border-radius: var(--radius-sm, 8px);
  color: var(--danger);
  background: var(--danger-surface);
  padding: 10px 14px;
  font-size: 13px;
}
.empty {
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-md, 12px);
  color: var(--text-tertiary);
  padding: 32px 16px;
  text-align: center;
  font-size: 13px;
}

/* Skeleton — uses theme tokens */
.skeleton {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 12px);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--background-surface);
  overflow: hidden;
  position: relative;
}
.skeleton::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, var(--background-raised) 50%, transparent 100%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}
.skeleton-line {
  height: 12px;
  border-radius: var(--radius-sm, 8px);
  background: var(--background-raised);
}
.skeleton-line:nth-child(1) { width: 55%; }
.skeleton-line:nth-child(2) { width: 80%; }
.skeleton-line:nth-child(3) { width: 40%; }
@keyframes shimmer {
  from { background-position: -200% 0; }
  to   { background-position:  200% 0; }
}

.load-more {
  align-self: center;
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill, 999px);
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 13px;
  padding: 8px 28px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.load-more:hover { color: var(--text-primary); border-color: var(--border-medium); }
.load-more:disabled { opacity: 0.5; cursor: default; }

.toast {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 100;
  background: var(--background-raised);
  border: 1px solid var(--brain-amber);
  border-radius: var(--radius-sm, 8px);
  color: var(--brain-amber);
  font-size: 13px;
  padding: 8px 16px;
}
.toast-enter-active, .toast-leave-active { transition: opacity 0.15s; }
.toast-enter-from, .toast-leave-to { opacity: 0; }

@media (max-width: 640px) {
  .pulse { padding: 12px; }
}
</style>
