<script setup lang="ts">
import { computed, ref } from 'vue'
import CreatorBadge from './CreatorBadge.vue'
import { ShareButton } from './ui'
import { logInteraction, type Post } from '../composables/useContent'

const props = defineProps<{
  post: Post
  topicName?: string
}>()

const emit = defineEmits<{
  (e: 'feedback', message: string): void
}>()

const TONE_META: Record<string, { cls: string; label: string }> = {
  critical:    { cls: 'tone--critical',    label: 'Critical' },
  supportive:  { cls: 'tone--supportive',  label: 'Supportive' },
  satirical:   { cls: 'tone--satirical',   label: 'Satirical' },
  informative: { cls: 'tone--informative', label: 'Intel' },
}

const tone = computed(() => (props.post.tone && props.post.tone in TONE_META ? TONE_META[props.post.tone] : null))

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

const shareText = computed(
  () => `${props.post.creator_name ?? 'Pulse'} on Pulse`,
)
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
      <span v-if="tone" :class="['tone', tone.cls]">{{ tone.label }}</span>
    </header>

    <div v-if="topicName" class="topic">{{ topicName }}</div>

    <img
      v-if="post.image_url"
      class="post-image"
      :src="post.image_url"
      :alt="post.image_prompt ?? 'post image'"
      loading="lazy"
    />

    <div class="body">{{ post.body }}</div>

    <footer class="card-actions">
      <button
        class="action"
        :class="{ active: voted === 'like' }"
        :disabled="sending"
        @click="vote('like')"
      >▲ Like</button>
      <button
        class="action"
        :class="{ active: voted === 'dislike' }"
        :disabled="sending"
        @click="vote('dislike')"
      >▼ Dislike</button>
      <ShareButton kind="pulse_post" :ref-id="post.id" :text="shareText" />
      <span class="post-score">{{ localScore.toFixed(2) }}</span>
    </footer>
  </article>
</template>

<style scoped>
.post-card {
  background: var(--background-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 12px);
  overflow: hidden;
}
.card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
}
.head-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 0;
  flex: 1;
}
.handle { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tone {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid;
  border-radius: var(--radius-pill, 999px);
  padding: 2px 8px;
}
.tone--critical    { color: var(--danger);  border-color: var(--danger); }
.tone--supportive  { color: var(--success); border-color: var(--success); }
.tone--satirical   { color: var(--brain-amber); border-color: var(--brain-amber); }
.tone--informative { color: var(--accent-primary); border-color: var(--accent-primary); }

.topic {
  padding: 8px 16px;
  font-size: 12px;
  color: var(--brain-amber);
  border-bottom: 1px solid var(--border-subtle);
}
.post-image {
  display: block;
  width: 100%;
  max-height: 300px;
  object-fit: cover;
  border-bottom: 1px solid var(--border-subtle);
}
.body {
  padding: 16px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}
.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-top: 1px solid var(--border-subtle);
}
.action {
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill, 999px);
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 13px;
  padding: 4px 12px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.action:hover { color: var(--text-primary); border-color: var(--border-medium); }
.action.active {
  color: var(--brain-amber);
  border-color: var(--brain-amber);
  background: var(--brain-amber-surface);
}
.action:disabled { opacity: 0.5; cursor: default; }
.post-score {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

@media (max-width: 640px) {
  .card-head { flex-wrap: wrap; }
}
</style>
