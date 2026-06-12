<script setup lang="ts">
import { computed, ref } from 'vue'
import CreatorBadge from './CreatorBadge.vue'
import { logInteraction, type Post } from '../composables/useContent'

const props = defineProps<{
  post: Post
  topicName?: string
}>()

const emit = defineEmits<{
  (e: 'feedback', message: string): void
}>()

const TONE_META: Record<string, { color: string; label: string }> = {
  critical:    { color: '#c94a4a', label: 'CRITICAL' },
  supportive:  { color: '#4ac94a', label: 'SUPPORTIVE' },
  satirical:   { color: '#c9a84c', label: 'SATIRICAL' },
  informative: { color: '#4a6fa5', label: 'INTEL' },
}

const tone = computed(() => (props.post.tone ? TONE_META[props.post.tone] : null))

const ago = computed(() => {
  const then = new Date(props.post.created_at).getTime()
  const mins = Math.max(0, Math.floor((Date.now() - then) / 60000))
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
})

// like | dislike | null — optimistic, local only
const voted = ref<'like' | 'dislike' | null>(null)
const localScore = ref(props.post.score)
const sending = ref(false)

async function vote(action: 'like' | 'dislike') {
  if (sending.value || voted.value === action) return
  const prev = voted.value
  voted.value = action
  // Optimistic nudge on the displayed score
  localScore.value = Math.min(1, Math.max(0, localScore.value + (action === 'like' ? 0.05 : -0.05)))
  sending.value = true
  try {
    await logInteraction(props.post.id, 'post', action)
    emit('feedback', 'FEEDBACK LOGGED')
  } catch {
    voted.value = prev
    localScore.value = props.post.score
    emit('feedback', 'TRANSMISSION FAILED')
  } finally {
    sending.value = false
  }
}

const copied = ref(false)
async function share() {
  try {
    await navigator.clipboard.writeText(
      `${window.location.origin}/pulse?post=${props.post.id}`,
    )
    copied.value = true
    emit('feedback', 'LINK COPIED')
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    emit('feedback', 'CLIPBOARD DENIED')
  }
}
</script>

<template>
  <article class="post-card">
    <header class="card-head">
      <CreatorBadge
        :name="post.creator_name"
        :slug="post.creator_slug"
        :avatar-url="post.creator_avatar"
        :score="post.creator_score"
        :bio="post.creator_bio"
        :size="40"
      />
      <div class="head-meta mono">
        <span v-if="post.creator_slug" class="handle">@{{ post.creator_slug }}</span>
        <span class="dot">·</span>
        <span class="time">{{ ago }}</span>
      </div>
      <span
        v-if="tone"
        class="tone mono"
        :style="{ borderColor: tone.color, color: tone.color }"
      >██ {{ tone.label }}</span>
    </header>

    <div v-if="topicName" class="topic mono">TOPIC: {{ topicName }} →</div>

    <img
      v-if="post.image_url"
      class="post-image"
      :src="post.image_url"
      :alt="post.image_prompt ?? 'post image'"
      loading="lazy"
    />

    <div class="body">{{ post.body }}</div>

    <footer class="card-actions mono">
      <button
        class="action"
        :class="{ active: voted === 'like' }"
        :disabled="sending"
        @click="vote('like')"
      >▲ LIKE</button>
      <button
        class="action"
        :class="{ active: voted === 'dislike' }"
        :disabled="sending"
        @click="vote('dislike')"
      >▼ DISLIKE</button>
      <button class="action" @click="share">→ {{ copied ? 'COPIED' : 'SHARE LINK' }}</button>
      <span class="post-score">[{{ localScore.toFixed(2) }}]</span>
    </footer>
  </article>
</template>

<style scoped>
.post-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 0;
}
.card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}
.head-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-2);
  min-width: 0;
  flex: 1;
}
.handle { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tone {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  border: 1px solid;
  padding: 2px 8px;
}
.topic {
  padding: 8px 16px;
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--accent-2);
  border-bottom: 1px solid var(--border);
  text-transform: uppercase;
}
.post-image {
  display: block;
  width: 100%;
  max-height: 300px;
  object-fit: cover;
  border-bottom: 1px solid var(--border);
}
.body {
  padding: 16px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-1);
  white-space: pre-wrap;
  word-break: break-word;
}
.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-top: 1px solid var(--border);
}
.action {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 0;
  color: var(--text-2);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  padding: 5px 12px;
  cursor: pointer;
  transition: color 0.12s, border-color 0.12s, background 0.12s;
}
.action:hover { color: var(--text-1); border-color: var(--accent); }
.action.active {
  color: var(--accent-2);
  border-color: var(--accent-2);
  background: rgba(196, 164, 85, 0.08);
}
.action:disabled { opacity: 0.5; cursor: default; }
.post-score {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-3);
}

@media (max-width: 640px) {
  .card-head { flex-wrap: wrap; }
}
</style>
