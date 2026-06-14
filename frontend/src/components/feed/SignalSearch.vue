<script setup lang="ts">
/** Inline SIGNAL search — a field + Cancel, then a vertical list of compact
 * result rows over the already-loaded videos. */
import { computed, ref } from 'vue'
import type { Video } from '../../composables/useContent'
import { seededThumb } from './seeded'
import { fmtSecs, isPlayable } from './video-util'

const props = defineProps<{ videos: Video[]; topicNames: Record<string, string> }>()
const emit = defineEmits<{ (e: 'play', v: Video): void; (e: 'cancel'): void }>()

const q = ref('')
const results = computed(() => {
  const s = q.value.trim().toLowerCase()
  if (!s) return []
  return props.videos.filter(
    (v) =>
      v.title.toLowerCase().includes(s) ||
      v.creator_name.toLowerCase().includes(s) ||
      (props.topicNames[v.topic_id] ?? '').toLowerCase().includes(s),
  )
})
</script>

<template>
  <div class="ss">
    <div class="ss__bar">
      <span class="ss__field">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.3-4.3"/></svg>
        <input v-model="q" autofocus placeholder="Search videos by topic…" />
      </span>
      <button class="ss__cancel" @click="emit('cancel')">Cancel</button>
    </div>

    <p v-if="!q.trim()" class="ss__hint">Search across {{ videos.length }} videos in your library.</p>
    <p v-else-if="results.length === 0" class="ss__hint">No videos match "{{ q }}".</p>
    <div v-else class="ss__list">
      <button v-for="v in results" :key="v.id" class="ss__row" :disabled="!isPlayable(v)" @click="emit('play', v)">
        <span class="ss__thumb" :style="v.thumbnail_url ? { backgroundImage: `url(${v.thumbnail_url})` } : seededThumb(v.creator_name)" />
        <span class="ss__meta">
          <span class="ss__title">{{ v.title }}</span>
          <span class="ss__sub">{{ v.creator_name.split(' ')[0] }} · <span class="t-mono">{{ fmtSecs(v.duration_seconds) }}</span></span>
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.ss { max-width: 720px; margin: 0 auto; padding: 8px 0 48px; }
.ss__bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.ss__field { flex: 1; display: flex; align-items: center; gap: 8px; height: 40px; padding: 0 12px; border-radius: var(--radius-sm); background: var(--background-input); border: 1px solid var(--border-subtle); color: var(--text-tertiary); }
.ss__field input { flex: 1; border: 0; background: transparent; color: var(--text-primary); font-size: var(--text-base); outline: none; }
.ss__cancel { background: none; border: 0; color: var(--accent-primary); cursor: pointer; font-size: var(--text-base); }
.ss__hint { text-align: center; padding: 24px 0; color: var(--text-tertiary); font-size: var(--text-sm); }
.ss__list { display: flex; flex-direction: column; }
.ss__row { display: flex; align-items: center; gap: 12px; padding: 8px 0; background: none; border: 0; cursor: pointer; text-align: left; }
.ss__row:disabled { opacity: 0.5; cursor: default; }
.ss__thumb { width: 56px; height: 42px; border-radius: 4px; flex: 0 0 auto; background-size: cover; background-position: center; }
.ss__meta { min-width: 0; }
.ss__title { display: block; font-size: var(--text-base); font-weight: 500; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ss__sub { display: block; font-size: var(--text-sm); color: var(--text-tertiary); }
</style>
