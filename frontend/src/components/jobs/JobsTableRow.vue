<script setup lang="ts">
import { ref } from 'vue'
import type { JobMatch, JobStatus } from '../../types/jobs'
import { useJobsStore } from '../../composables/useJobsStore'

const props = defineProps<{ match: JobMatch }>()

const store = useJobsStore()
const saving = ref(false)
const saveError = ref<string | null>(null)
let errorTimer: ReturnType<typeof setTimeout> | null = null

function scoreClass(score: number): string {
  if (score >= 70) return 'score--green'
  if (score >= 50) return 'score--amber'
  return 'score--red'
}

function remoteClass(type: string): string {
  const map: Record<string, string> = { remote: 'remote--green', hybrid: 'remote--blue', onsite: 'remote--gray' }
  return map[type] ?? 'remote--muted'
}

function rowClass(match: JobMatch): string {
  if (match.status === 'applied' || match.status === 'interviewing') return 'row--applied'
  if (match.status === 'rejected' || match.status === 'withdrawn')   return 'row--muted'
  if (match.match_tier === 'STRONG_MATCH')                           return 'row--strong'
  return ''
}

function platformLabel(p: string): string {
  const map: Record<string, string> = {
    'jobs.ch': 'jobs.ch',
    linkedin: 'LinkedIn',
    indeed: 'Indeed',
    stepstone: 'StepStone',
  }
  return map[p] ?? p
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(new Date(iso))
  } catch {
    return iso.slice(0, 10)
  }
}

async function onStatusChange(event: Event): Promise<void> {
  const select = event.target as HTMLSelectElement
  const newStatus = select.value as JobStatus
  const prevStatus = props.match.status
  if (newStatus === prevStatus) return

  saving.value = true
  saveError.value = null

  try {
    await store.updateStatus(props.match.id, newStatus)
  } catch (err) {
    select.value = prevStatus
    saveError.value = err instanceof Error ? err.message : 'Save failed'
    if (errorTimer) clearTimeout(errorTimer)
    errorTimer = setTimeout(() => { saveError.value = null }, 4000)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <tr :class="['match-row', rowClass(match)]">
    <!-- Score -->
    <td class="col-score">
      <span :class="['score-badge', scoreClass(match.match_score)]">{{ match.match_score }}</span>
    </td>

    <!-- Title -->
    <td class="col-title">
      <a :href="match.job_url" target="_blank" rel="noopener noreferrer" class="title-link">
        {{ match.title }}
      </a>
    </td>

    <!-- Company -->
    <td class="col-company">{{ match.company }}</td>

    <!-- Location -->
    <td class="col-location">{{ match.location }}, {{ match.country }}</td>

    <!-- Salary -->
    <td class="col-salary">{{ match.salary_raw ?? '—' }}</td>

    <!-- Remote -->
    <td class="col-remote">
      <span :class="['remote-pill', remoteClass(match.remote_type)]">{{ match.remote_type }}</span>
    </td>

    <!-- Platform -->
    <td class="col-platform">{{ platformLabel(match.platform) }}</td>

    <!-- Found date -->
    <td class="col-date">{{ formatDate(match.run_timestamp) }}</td>

    <!-- Status -->
    <td class="col-status">
      <div class="status-cell">
        <select
          :value="match.status"
          :disabled="saving"
          :aria-label="`Status for ${match.title} at ${match.company}`"
          :class="['status-select', `status--${match.status}`]"
          @change="onStatusChange"
        >
          <option value="new">New</option>
          <option value="reviewing">Reviewing</option>
          <option value="applied">Applied</option>
          <option value="interviewing">Interviewing</option>
          <option value="rejected">Rejected</option>
          <option value="withdrawn">Withdrawn</option>
          <option value="expired">Expired</option>
        </select>
        <span v-if="saving" class="saving-indicator">Saving…</span>
        <span v-if="saveError" class="save-error">{{ saveError }}</span>
      </div>
    </td>

    <!-- AI Summary -->
    <td class="col-summary">
      <span
        v-if="match.ai_summary"
        class="summary-text"
        :title="match.ai_summary"
      >{{ match.ai_summary }}</span>
      <span v-else class="no-summary">—</span>
    </td>
  </tr>
</template>

<style scoped>
.match-row td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  color: var(--text-1);
  vertical-align: middle;
}
.match-row:last-child td { border-bottom: none; }
.match-row:hover td { background: rgba(255,255,255,0.02); }

/* Left-border accent */
.match-row.row--applied { border-left: 2px solid var(--accent); }
.match-row.row--strong  { border-left: 2px solid var(--success); }
.match-row.row--muted td { opacity: 0.4; }

/* Score */
.score-badge {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  min-width: 36px;
  text-align: center;
}
.score--green { background: rgba(58,122,90,0.22); color: var(--status-active); }
.score--amber { background: rgba(138,106,32,0.22); color: var(--status-processing); }
.score--red   { background: rgba(122,58,58,0.22);  color: var(--status-error); }

/* Title */
.col-title { max-width: 260px; }
.title-link {
  color: var(--text-1);
  text-decoration: none;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.title-link:hover { color: var(--accent); }

/* Remote pill */
.remote-pill {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 2px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.remote--green { background: rgba(58,122,90,0.18); color: var(--status-active); }
.remote--blue  { background: rgba(74,127,165,0.18); color: var(--accent); }
.remote--gray  { background: var(--border); color: var(--text-2); }
.remote--muted { color: var(--text-3); }

/* Date */
.col-date {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-3);
  white-space: nowrap;
}

/* Status */
.status-cell { position: relative; display: inline-block; }
.status-select {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 2px;
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 4px 8px;
  cursor: pointer;
  appearance: none;
  min-width: 110px;
}
.status-select:focus  { outline: 1px solid var(--accent); }
.status-select:disabled { opacity: 0.5; cursor: not-allowed; }

.status--new          { color: var(--status-processing); }
.status--reviewing    { color: var(--accent); }
.status--applied      { color: var(--status-active); }
.status--interviewing { color: #6ee7b7; }
.status--rejected     { color: var(--status-error); }
.status--withdrawn    { color: var(--text-3); }
.status--expired      { color: var(--text-3); }

.saving-indicator {
  font-size: 10px;
  color: var(--text-3);
  font-family: var(--font-mono);
  letter-spacing: 0.06em;
  white-space: nowrap;
  margin-left: 6px;
}
.save-error {
  display: block;
  font-size: 10px;
  color: var(--status-error);
  margin-top: 2px;
  font-family: var(--font-mono);
}

/* AI Summary */
.col-summary { max-width: 280px; }
.summary-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.5;
  cursor: default;
}
.no-summary { color: var(--text-3); }
</style>
