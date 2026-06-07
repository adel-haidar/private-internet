<script setup lang="ts">
import { computed } from 'vue'
import { useJobsStore } from '../../composables/useJobsStore'

defineProps<{ reportOpen: boolean }>()
defineEmits<{ 'toggle-report': [] }>()

const store = useJobsStore()

const lastRunText = computed((): string => {
  if (!store.state.lastRunAt) return 'Never run'
  const diff = Date.now() - new Date(store.state.lastRunAt).getTime()
  const mins  = Math.floor(diff / 60_000)
  const hours = Math.floor(diff / 3_600_000)
  const days  = Math.floor(diff / 86_400_000)
  if (mins  <  1) return 'Last run: just now'
  if (mins  < 60) return `Last run: ${mins}m ago`
  if (hours < 24) return `Last run: ${hours}h ago`
  return `Last run: ${days}d ago`
})
</script>

<template>
  <header class="jobs-header">
    <div class="header-left">
      <h1 class="page-title">Job Hunt</h1>
      <p class="page-sub">Switzerland · Canada · Norway · Singapore</p>
    </div>

    <div class="header-right">
      <div class="btn-group">
        <button
          class="btn btn-secondary"
          :aria-pressed="reportOpen"
          @click="$emit('toggle-report')"
        >
          {{ reportOpen ? 'Hide Report' : 'View Report' }}
        </button>

        <button
          class="btn btn-primary run-btn"
          :disabled="store.state.isRunning"
          aria-label="Run job hunt agent"
          @click="store.triggerRun()"
        >
          <span v-if="store.state.isRunning" class="spinner" aria-hidden="true"></span>
          {{ store.state.isRunning ? 'Running…' : 'Run Agent' }}
        </button>
      </div>

      <p class="last-run-text">{{ lastRunText }}</p>
    </div>
  </header>
</template>

<style scoped>
.jobs-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.page-title {
  font-size: 22px;
  font-weight: 500;
  color: var(--text-1);
  line-height: 1.2;
}

.page-sub {
  font-size: 13px;
  color: var(--text-2);
  margin-top: 4px;
}

.header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
}

.btn-group {
  display: flex;
  gap: 8px;
}

.run-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 110px;
  justify-content: center;
}
.run-btn:disabled { opacity: 0.7; cursor: not-allowed; }

.spinner {
  width: 12px;
  height: 12px;
  border: 1.5px solid rgba(255,255,255,0.25);
  border-top-color: var(--text-1);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

.last-run-text {
  font-size: 12px;
  color: var(--text-3);
  font-family: var(--font-mono);
  letter-spacing: 0.06em;
}
</style>
