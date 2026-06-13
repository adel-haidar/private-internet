<script setup lang="ts">
import PageHead from '../components/ui/PageHead.vue'
</script>

<template>
  <div class="overview-page">
    <PageHead title="Overview" desc="A summary of your private intelligence network." />
    <div class="placeholder">
      <p class="t-secondary">This module is coming soon.</p>
    </div>
  </div>
</template>

<style scoped>
.overview-page {
  padding: var(--space-8, 32px);
}
.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 12px);
  background: var(--background-surface);
}
</style>
