<script setup lang="ts">
/** A horizontal-scroll filter pill (tone for PULSE, category for SIGNAL).
 * Inactive = colour as text + border; active = filled with the colour (amber
 * uses its surface + amber text instead of a filled amber pill). */
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{ label: string; active: boolean; color?: string }>(),
  { color: 'var(--accent-primary)' },
)
defineEmits<{ (e: 'click'): void }>()

const isAmber = computed(() => props.color === 'var(--brain-amber)')
const style = computed(() => {
  if (!props.active) return { color: props.color, borderColor: props.color }
  if (isAmber.value) return { background: 'var(--brain-amber-surface)', color: 'var(--brain-amber)', borderColor: 'var(--brain-amber)' }
  return { background: props.color, color: '#fff', borderColor: props.color }
})
</script>

<template>
  <button class="chip" :style="style" @click="$emit('click')">{{ label }}</button>
</template>

<style scoped>
.chip {
  flex: 0 0 auto;
  height: 32px;
  padding: 0 14px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  font-family: var(--font-display);
  font-weight: 500;
  font-size: var(--text-sm);
  background: transparent;
  border: 1px solid;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.15s, color 0.15s, border-color 0.15s;
}
</style>
