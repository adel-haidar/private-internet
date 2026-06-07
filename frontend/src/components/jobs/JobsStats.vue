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
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stat-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-2);
}

.stat-value {
  font-size: 24px;
  font-weight: 500;
  color: var(--text-1);
  line-height: 1;
}

.stat-card--green  .stat-value { color: var(--status-active); }
.stat-card--blue   .stat-value { color: var(--accent); }
.stat-card--amber  .stat-value { color: var(--status-processing); }
</style>
