<script setup lang="ts">
/** Circular creator avatar: network image if present, else seeded-colour fill
 * with white initials. */
import { computed } from 'vue'
import { seededColor, initials } from './seeded'

const props = withDefaults(defineProps<{ name: string; image?: string | null; size?: number }>(), {
  size: 36,
})

const color = computed(() => seededColor(props.name))
</script>

<template>
  <span
    class="sa"
    :style="{ width: size + 'px', height: size + 'px', background: image ? undefined : color, fontSize: size * 0.4 + 'px' }"
  >
    <img v-if="image" :src="image" :alt="name" />
    <template v-else>{{ initials(name) }}</template>
  </span>
</template>

<style scoped>
.sa {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  overflow: hidden;
  flex: 0 0 auto;
  color: #fff;
  font-family: var(--font-display);
  font-weight: 600;
  line-height: 1;
  user-select: none;
}
.sa img { width: 100%; height: 100%; object-fit: cover; }
</style>
