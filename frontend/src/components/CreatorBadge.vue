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
// Palette values are kept as literal hex (used inside an SVG fill attr) — they're
// decorative, not theme-sensitive, so hardcoding is acceptable here.
const PALETTE = ['#5B5BD6', '#E8A444', '#2D7A4F', '#B45309', '#7C5CB5', '#C0392B']

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
      <rect x="0" y="0" width="5" height="5" fill="transparent" />
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
    <span class="name">{{ name }}</span>
    <span v-if="score !== undefined" class="score t-mono" :class="scoreClass">
      {{ score.toFixed(2) }}
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
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm, 8px);
  object-fit: cover;
  display: block;
  image-rendering: pixelated;
}
.name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.score {
  font-size: 12px;
  flex-shrink: 0;
}
.score-high { color: var(--success); }
.score-mid  { color: var(--brain-amber); }
.score-low  { color: var(--danger); }
.status-dot { font-size: 10px; flex-shrink: 0; }
.status-dot.on  { color: var(--success); }
.status-dot.off { color: var(--text-tertiary); }
</style>
