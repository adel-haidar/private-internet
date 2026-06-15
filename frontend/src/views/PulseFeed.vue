<script setup lang="ts">
/**
 * PULSE — editorial feed: masthead → tone chips → featured hero → variable
 * format cards (A/B/C, with paired text-only duos) → reading mode. A curated
 * personal magazine, not an RSS list.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { usePulseFeed, logInteraction, type Post, type Tone } from '../composables/useContent'
import { useToast } from '../components/ui/useToast'
import FeedChip from '../components/feed/FeedChip.vue'
import FeaturedCard from '../components/feed/FeaturedCard.vue'
import TonePill from '../components/feed/TonePill.vue'
import ScoreText from '../components/feed/ScoreText.vue'
import FeedVoteButton from '../components/feed/FeedVoteButton.vue'
import PulsePostCard from '../components/feed/PulsePostCard.vue'
import PulseReader from '../components/feed/PulseReader.vue'
import PulseFilterPanel from '../components/feed/PulseFilterPanel.vue'
import { headline, readMinutes } from '../components/feed/post-format'

const { posts, loading, error, hasMore, loadMore, sort, setSort } = usePulseFeed()
const toast = useToast()

const TONES: (Tone | 'all')[] = ['all', 'informative', 'satirical', 'critical', 'supportive']
const TONE_COLOR: Record<string, string> = {
  all: 'var(--accent-primary)',
  informative: 'var(--accent-primary)',
  satirical: 'var(--brain-amber)',
  critical: 'var(--danger)',
  supportive: 'var(--success)',
}
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

const tone = ref<Tone | 'all'>('all')
const creator = ref<string | null>(null)
const panelOpen = ref(false)
const reading = ref<Post | null>(null)
const votes = reactive<Record<string, 'up' | 'down'>>({})

onMounted(() => loadMore())

const creators = computed(() => {
  const seen = new Map<string, string>()
  for (const p of posts.value) if (!seen.has(p.creator_id)) seen.set(p.creator_id, p.creator_name)
  return [...seen].map(([id, name]) => ({ id, name }))
})

const filtered = computed(() =>
  posts.value.filter(
    (p) => (tone.value === 'all' || p.tone === tone.value) && (creator.value === null || p.creator_id === creator.value),
  ),
)

const featured = computed<Post | null>(() =>
  filtered.value.length ? filtered.value.reduce((a, b) => (a.score >= b.score ? a : b)) : null,
)

// Remaining posts (everything but the hero) flow into a masonry of columns on
// wide screens, so the feed fills the width instead of a single narrow column.
const rest = computed<Post[]>(() => filtered.value.filter((p) => p.id !== featured.value?.id))

async function vote(post: Post, like: boolean) {
  votes[post.id] = like ? 'up' : 'down'
  try {
    await logInteraction(post.id, 'post', like ? 'like' : 'dislike')
    toast('Feedback saved')
  } catch { /* best-effort */ }
}
</script>

<template>
  <div class="pulse">
    <!-- masthead -->
    <div class="pulse__masthead">
      <span class="pulse__title">PULSE</span>
      <button class="pulse__filter" aria-label="Filters" @click="panelOpen = true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
          <path d="M4 6h11M19 6h1M4 12h4M12 12h8M4 18h9M17 18h3" /><circle cx="17" cy="6" r="2" /><circle cx="10" cy="12" r="2" /><circle cx="15" cy="18" r="2" />
        </svg>
      </button>
    </div>

    <!-- tone chips -->
    <div class="pulse__chips">
      <FeedChip v-for="t in TONES" :key="t" :label="cap(t)" :color="TONE_COLOR[t]" :active="tone === t" @click="tone = t" />
    </div>

    <!-- loading / error -->
    <div v-if="loading && posts.length === 0" class="pulse__skeleton">
      <div v-for="n in 4" :key="n" class="pulse__sk" />
    </div>
    <div v-else-if="error" class="pulse__error">
      <p>Couldn't load your feed.</p>
      <button class="pulse__retry" @click="loadMore">Try again</button>
    </div>

    <template v-else>
      <div class="pulse__feed">
        <!-- featured (spans full width above the masonry) -->
        <div v-if="featured" class="pulse__feat">
          <FeaturedCard
            :seed="featured.creator_name"
            :image="featured.image_url"
            :title="headline(featured.body)"
            :meta-name="featured.creator_name"
            :meta-trailing="`· ${readMinutes(featured.body)} min read`"
            @click="reading = featured"
          >
            <template #topLeft><TonePill v-if="featured.tone" :tone="featured.tone" /></template>
            <template #topRight><ScoreText :score="featured.score" on-dark /></template>
          </FeaturedCard>
          <div class="pulse__featactions">
            <FeedVoteButton :label="`${featured.score.toFixed(2)} Like`" color="var(--success)" icon="up" :active="votes[featured.id] === 'up'" @click="vote(featured, true)" />
            <FeedVoteButton label="Dislike" color="var(--danger)" icon="down" :active="votes[featured.id] === 'down'" @click="vote(featured, false)" />
            <FeedVoteButton label="Open" color="var(--accent-primary)" icon="open" @click="reading = featured" />
          </div>
        </div>

        <!-- post masonry -->
        <div class="pulse__masonry">
          <PulsePostCard
            v-for="p in rest" :key="p.id" :post="p"
            :vote="votes[p.id] ?? null" @vote="(l) => vote(p, l)" @open="reading = p"
          />
        </div>

        <div v-if="filtered.length === 0" class="pulse__empty">
          Nothing here yet. Add to your brain and your feed will fill with stories.
        </div>

        <button v-if="hasMore() && filtered.length" class="pulse__more" :disabled="loading" @click="loadMore">
          {{ loading ? 'Loading…' : 'Load more' }}
        </button>
      </div>
    </template>

    <PulseReader
      v-if="reading"
      :post="reading"
      :vote="votes[reading.id] ?? null"
      @vote="(l) => vote(reading!, l)"
      @close="reading = null"
    />
    <PulseFilterPanel
      v-if="panelOpen"
      :sort="sort"
      :tone="tone"
      :creator="creator"
      :creators="creators"
      @update:sort="setSort"
      @update:tone="(t) => (tone = t)"
      @update:creator="(c) => (creator = c)"
      @close="panelOpen = false"
    />
  </div>
</template>

<style scoped>
.pulse { max-width: var(--content-dashboard); margin: 0 auto; padding: 8px 0 48px; }
.pulse__masthead { display: flex; align-items: center; justify-content: space-between; padding: 0 4px 12px; }
.pulse__title { font-family: var(--font-display); font-weight: 600; font-size: 15px; letter-spacing: 0.1em; color: var(--text-primary); }
.pulse__filter { background: none; border: 0; color: var(--text-primary); cursor: pointer; display: flex; padding: 6px; }
.pulse__chips { display: flex; gap: 8px; overflow-x: auto; padding: 2px 4px 18px; }
.pulse__feed { display: flex; flex-direction: column; gap: 14px; }
.pulse__featactions { display: flex; gap: 6px; margin-top: 10px; }
/* The hero spans the full feed width as a banner above the masonry. */
.pulse__feat { width: 100%; }
/* Masonry: single column by default, more columns as width allows. CSS columns
   keep each card intact (break-inside) while letting the feed fill the page. */
.pulse__masonry { display: flex; flex-direction: column; gap: 14px; }
@media (min-width: 1000px) {
  .pulse__masonry { display: block; column-count: 2; column-gap: 16px; }
  .pulse__masonry > * { break-inside: avoid; margin: 0 0 16px; }
}
@media (min-width: 1440px) {
  .pulse__masonry { column-count: 3; }
}
.pulse__skeleton { display: flex; flex-direction: column; gap: 14px; }
.pulse__sk { height: 160px; border-radius: var(--radius-md); background: var(--background-raised); animation: pulse-sk 1.4s ease-in-out infinite; }
@keyframes pulse-sk { 0%, 100% { opacity: 0.6; } 50% { opacity: 1; } }
.pulse__error, .pulse__empty { text-align: center; padding: 48px 16px; color: var(--text-secondary); font-family: var(--font-serif); }
.pulse__retry { margin-top: 12px; height: 36px; padding: 0 16px; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); background: transparent; color: var(--text-secondary); cursor: pointer; }
.pulse__more { align-self: center; margin-top: 8px; height: 40px; padding: 0 24px; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); background: transparent; color: var(--text-secondary); cursor: pointer; font-size: var(--text-sm); }
</style>
