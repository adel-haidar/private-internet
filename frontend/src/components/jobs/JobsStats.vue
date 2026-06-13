<script setup lang="ts">
import { useJobsStore } from '../../composables/useJobsStore'

const store = useJobsStore()
</script>

<template>
  <div class="stats-row">
    <div class="stat-card">
      <span class="stat-label">Total matches</span>
      <span class="stat-value">{{ store.state.totalCount }}</span>
    </div>
    <div class="stat-card stat-card--green">
      <span class="stat-label">Strong matches</span>
      <span class="stat-value">{{ store.strongMatchCount }}</span>
    </div>
    <div class="stat-card stat-card--blue">
      <span class="stat-label">Applied / interviewing</span>
      <span class="stat-value">{{ store.appliedCount }}</span>
    </div>
    <div class="stat-card stat-card--amber">
      <span class="stat-label">New (unreviewed)</span>
      <span class="stat-value">{{ store.newCount }}</span>
    </div>
  </div>
</template>

<style scoped>
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  padding: 14px 0;
  flex-shrink: 0;
}

.stat-card {
  background: var(--background-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 12px);
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stat-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.stat-value {
  font-size: 24px;
  font-weight: 500;
  color: var(--text-primary);
  line-height: 1;
}

.stat-card--green  .stat-value { color: var(--success); }
.stat-card--blue   .stat-value { color: var(--accent-primary); }
.stat-card--amber  .stat-value { color: var(--brain-amber); }
</style>
