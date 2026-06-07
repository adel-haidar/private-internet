<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useJobsStore } from '../composables/useJobsStore'
import JobsHeader from '../components/jobs/JobsHeader.vue'
import JobsStats from '../components/jobs/JobsStats.vue'
import JobsFilters from '../components/jobs/JobsFilters.vue'
import JobsTable from '../components/jobs/JobsTable.vue'
import JobRunProgress from '../components/jobs/JobRunProgress.vue'
import JobsReportPanel from '../components/jobs/JobsReportPanel.vue'

const store = useJobsStore()
const showReport = ref(false)

onMounted(async () => {
  await Promise.all([store.fetchMatches(), store.fetchReport()])
})
</script>

<template>
  <div class="jobs-view">
    <div v-if="store.state.error" class="error-banner">
      <span>{{ store.state.error }}</span>
      <button class="error-dismiss" aria-label="Dismiss error" @click="store.clearError()">✕</button>
    </div>

    <JobsHeader @toggle-report="showReport = !showReport" :report-open="showReport" />
    <JobsStats />
    <JobsFilters />
    <JobRunProgress />

    <div class="table-wrap">
      <JobsTable />
    </div>

    <JobsReportPanel :expanded="showReport" @toggle="showReport = !showReport" />
  </div>
</template>

<style scoped>
.jobs-view {
  display: flex;
  flex-direction: column;
  height: calc(100svh - var(--header-h) - var(--gutter) * 2);
  min-height: 0;
  gap: 0;
}

.error-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  margin-bottom: 12px;
  background: rgba(122, 58, 58, 0.18);
  border: 1px solid var(--danger);
  border-radius: 2px;
  font-size: 13px;
  color: #e88;
  flex-shrink: 0;
}

.error-dismiss {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 14px;
  padding: 0 4px;
  opacity: 0.7;
  flex-shrink: 0;
}
.error-dismiss:hover { opacity: 1; }

.table-wrap {
  flex: 1 1 auto;
  overflow-y: auto;
  min-height: 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
</style>
