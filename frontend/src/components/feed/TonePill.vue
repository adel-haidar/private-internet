<script setup lang="ts">
/** Tone pill — Critical=danger/white · Satirical=amber-surface/amber ·
 * Supportive=success/white · Informative=accent-surface/accent. */
import { computed } from 'vue'
import type { Tone } from '../../composables/useContent'

const props = defineProps<{ tone: Tone }>()

const MAP: Record<Tone, { bg: string; fg: string }> = {
  critical: { bg: 'var(--danger)', fg: '#fff' },
  satirical: { bg: 'var(--brain-amber-surface)', fg: 'var(--brain-amber)' },
  supportive: { bg: 'var(--success)', fg: '#fff' },
  informative: { bg: 'var(--accent-surface)', fg: 'var(--accent-primary)' },
}
const s = computed(() => MAP[props.tone] ?? MAP.informative)
const label = computed(() => props.tone.charAt(0).toUpperCase() + props.tone.slice(1))
</script>

<template>
  <span class="tone" :style="{ background: s.bg, color: s.fg }">{{ label }}</span>
</template>

<style scoped>
.tone {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--text-xs);
  white-space: nowrap;
}
</style>
