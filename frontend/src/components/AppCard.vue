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
  border-radius: 2px;
  position: relative;
  padding: var(--gutter);
}
.card.corner::before,
.card.corner::after {
  content: "";
  position: absolute;
  width: 10px;
  height: 10px;
  pointer-events: none;
}
.card.corner::before {
  top: -1px; left: -1px;
  border-top: 1px solid var(--accent);
  border-left: 1px solid var(--accent);
}
.card.corner::after {
  bottom: -1px; right: -1px;
  border-bottom: 1px solid var(--accent);
  border-right: 1px solid var(--accent);
}
</style>
