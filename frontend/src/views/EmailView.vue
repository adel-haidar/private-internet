<script setup lang="ts">
import PageHead from '../components/ui/PageHead.vue'
</script>

<template>
  <div class="email-page">
    <PageHead title="Email" desc="Intelligent email triage, summaries, and drafts." />
    <div class="placeholder">
      <p class="t-secondary">This module is coming soon.</p>
    </div>
  </div>
</template>

<style scoped>
.email-page {
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
