<script setup lang="ts">
/** Background-less mono score, 2 decimals, coloured: green >0.65 / amber
 * 0.4–0.65 / red <0.4 (white when [onDark]). */
import { computed } from 'vue'

const props = withDefaults(defineProps<{ score: number; onDark?: boolean }>(), { onDark: false })

const color = computed(() => {
  if (props.onDark) return '#fff'
  if (props.score > 0.65) return 'var(--success)'
  if (props.score >= 0.4) return 'var(--brain-amber)'
  return 'var(--danger)'
})
</script>

<template>
  <span class="score t-mono" :style="{ color }">{{ score.toFixed(2) }}</span>
</template>

<style scoped>
.score { font-family: var(--font-mono); font-size: var(--text-xs); font-weight: 500; }
</style>
