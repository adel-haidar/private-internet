<script setup lang="ts">
defineProps<{ corner?: boolean }>()
</script>

<template>
  <div class="card" :class="{ corner }">
    <slot></slot>
  </div>
</template>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md, 12px);
  position: relative;
  padding: var(--gutter);
}
/* .corner variant: subtle accent border emphasis */
.card.corner {
  border-color: var(--accent-primary);
}
</style>
