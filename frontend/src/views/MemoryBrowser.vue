<script setup lang="ts">
import MemorySection from '../components/MemorySection.vue'
</script>

<template>
  <div class="page">
    <header class="page-header">
      <span class="page-tag">SECTION</span>
      <h1 class="page-title">MEMORY</h1>
    </header>
    <div class="rule" />
    <div class="body">
      <MemorySection />
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  align-items: baseline;
  gap: 16px;
  padding: 28px 32px 24px;
}

.page-tag {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.14em;
  color: var(--text-muted);
  border: 1px solid var(--border);
  padding: 2px 6px;
}

.page-title {
  font-family: var(--font-mono);
  font-size: 18px;
  letter-spacing: 0.07em;
  color: var(--text-primary);
}

.rule {
  height: 1px;
  background: var(--border);
}

.body {
  padding: 28px 32px 40px;
  flex: 1;
}
</style>
