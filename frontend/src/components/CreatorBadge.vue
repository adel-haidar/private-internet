<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    name: string
    slug?: string
    avatarUrl?: string | null
    score?: number
    bio?: string
    size?: number
  }>(),
  { size: 32 },
)

// Deterministic geometric avatar: hash the slug into a mirrored 5x5 cell grid
// + a palette color. Same slug → same avatar, no asset needed.
const PALETTE = ['#4A7FA5', '#C4A455', '#3A7A5A', '#8A6A20', '#7A5AA5', '#A55A4A']

function hash(s: string): number {
  let h = 0x811c9dc5
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 0x01000193)
  }
  return h >>> 0
}

const seed = computed(() => hash(props.slug || props.name))

const avatarColor = computed(() => PALETTE[seed.value % PALETTE.length])

const cells = computed(() => {
  const out: Array<{ x: number; y: number }> = []
  let bits = seed.value
  for (let y = 0; y < 5; y++) {
    for (let x = 0; x < 3; x++) {
      bits = (Math.imul(bits, 1103515245) + 12345) >>> 0
      if (bits % 5 < 2) {
        out.push({ x, y })
        if (x < 2) out.push({ x: 4 - x, y }) // mirror for symmetry
      }
    }
  }
  return out
})

const scoreClass = computed(() => {
  if (props.score === undefined) return ''
  if (props.score > 0.6) return 'score-high'
  if (props.score >= 0.4) return 'score-mid'
  return 'score-low'
})

const active = computed(() => props.score === undefined || props.score >= 0.3)
</script>

<template>
  <div class="creator-badge" :title="bio || name">
    <img
      v-if="avatarUrl"
      class="avatar"
      :src="avatarUrl"
      :alt="name"
      :style="{ width: size + 'px', height: size + 'px' }"
    />
    <svg
      v-else
      class="avatar"
      :width="size"
      :height="size"
      viewBox="0 0 5 5"
      :style="{ width: size + 'px', height: size + 'px' }"
      role="img"
      :aria-label="name"
    >
      <rect x="0" y="0" width="5" height="5" fill="#141620" />
      <rect
        v-for="(c, i) in cells"
        :key="i"
        :x="c.x"
        :y="c.y"
        width="1"
        height="1"
        :fill="avatarColor"
      />
    </svg>
    <span class="name mono">{{ name.toUpperCase() }}</span>
    <span v-if="score !== undefined" class="score mono" :class="scoreClass">
      [{{ score.toFixed(2) }}]
    </span>
    <span class="status-dot" :class="active ? 'on' : 'off'">{{ active ? '●' : '○' }}</span>
  </div>
</template>

<style scoped>
.creator-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.avatar {
  flex-shrink: 0;
  border: 1px solid var(--border);
  border-radius: 0;
  object-fit: cover;
  display: block;
  image-rendering: pixelated;
}
.name {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.score {
  font-size: 11px;
  flex-shrink: 0;
}
.score-high { color: var(--status-active); }
.score-mid  { color: var(--accent-2); }
.score-low  { color: var(--status-error); }
.status-dot { font-size: 9px; flex-shrink: 0; }
.status-dot.on  { color: var(--status-active); }
.status-dot.off { color: var(--text-3); }
</style>
