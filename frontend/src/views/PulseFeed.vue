<script setup lang="ts">
import { onMounted, ref } from 'vue'
import PostCard from '../components/PostCard.vue'
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
        <h1 class="title mono">PULSE // AI CONTENT FEED</h1>
        <span class="count mono" v-if="total">{{ total }} DISPATCHES</span>
      </div>
      <div class="sort-row mono">
        <span class="sort-label">SORT:</span>
        <button
          v-for="s in SORTS"
          :key="s.id"
          class="sort-tab"
          :class="{ active: sort === s.id }"
          @click="setSort(s.id)"
        >[{{ s.label }}]</button>
      </div>
    </div>

    <div v-if="error" class="error mono">// TRANSMISSION ERROR: {{ error }}</div>

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

      <div v-if="!loading && posts.length === 0 && !error" class="empty mono">
        // NO DISPATCHES ON FILE — RUN THE POST GENERATION JOB
      </div>
    </div>

    <button
      v-if="hasMore() && posts.length > 0"
      class="load-more mono"
      :disabled="loading"
      @click="loadMore"
    >{{ loading ? 'RETRIEVING...' : '[LOAD MORE]' }}</button>

    <Transition name="toast">
      <div v-if="toast" class="toast mono">{{ toast }}</div>
    </Transition>
  </div>
</template>

<style scoped>
.pulse {
  max-width: 680px;
  margin: 0 auto;
  padding: var(--gutter);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.pulse-head {
  border: 1px solid var(--border);
  background: var(--surface);
}
.title-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
}
.title {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.12em;
}
.count {
  font-size: 10px;
  color: var(--text-3);
  letter-spacing: 0.08em;
  white-space: nowrap;
}
.sort-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  font-size: 11px;
}
.sort-label { color: var(--text-3); margin-right: 6px; letter-spacing: 0.08em; }
.sort-tab {
  background: transparent;
  border: none;
  border-radius: 0;
  color: var(--text-2);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  padding: 3px 6px;
  cursor: pointer;
}
.sort-tab:hover { color: var(--text-1); }
.sort-tab.active { color: var(--accent-2); }

.feed {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.error {
  border: 1px solid var(--danger);
  color: var(--status-error);
  background: rgba(122, 58, 58, 0.08);
  padding: 10px 14px;
  font-size: 12px;
}
.empty {
  border: 1px dashed var(--border);
  color: var(--text-3);
  padding: 32px 16px;
  text-align: center;
  font-size: 12px;
  letter-spacing: 0.06em;
}

/* Skeleton — horizontal scan per design system */
.skeleton {
  border: 1px solid var(--border);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: repeating-linear-gradient(90deg, #12121a 0px, #1e1e2e 40px, #12121a 80px);
  background-size: 200% 100%;
  animation: scan 1.5s infinite linear;
}
.skeleton-line {
  font-size: 12px;
  color: var(--text-3);
  opacity: 0.5;
  user-select: none;
}
@keyframes scan {
  from { background-position: 0% 0; }
  to { background-position: -200% 0; }
}

.load-more {
  align-self: center;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 0;
  color: var(--text-2);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.1em;
  padding: 10px 28px;
  cursor: pointer;
  transition: color 0.12s, border-color 0.12s;
}
.load-more:hover { color: var(--text-1); border-color: var(--accent); }
.load-more:disabled { opacity: 0.5; cursor: default; }

.toast {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 100;
  background: var(--elevated);
  border: 1px solid var(--accent-2);
  color: var(--accent-2);
  font-size: 11px;
  letter-spacing: 0.1em;
  padding: 8px 16px;
}
.toast-enter-active, .toast-leave-active { transition: opacity 0.15s; }
.toast-enter-from, .toast-leave-to { opacity: 0; }

@media (max-width: 640px) {
  .pulse { padding: 12px; }
}
</style>
