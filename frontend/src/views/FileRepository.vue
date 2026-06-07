<script setup lang="ts">
import { computed } from 'vue'
import { useFileUpload } from '../composables/useFileUpload'
import UploadZone  from '../components/UploadZone.vue'
import UploadQueue from '../components/UploadQueue.vue'

const { files, uploadFile, removeFile, clearCompleted, uploadAll } = useFileUpload()

const hasQueued    = computed(() => files.value.some((f) => f.status === 'queued'))
const hasCompleted = computed(() => files.value.some((f) => f.status === 'success'))

function handleFiles(incoming: File[]) {
  // Each call is unawaited — queue processor runs sequentially internally.
  incoming.forEach((f) => uploadFile(f))
}
</script>

<template>
  <div class="page">
    <!-- Section header -->
    <header class="page-header">
      <span class="page-tag">SECTION</span>
      <h1 class="page-title">FILE REPOSITORY</h1>
    </header>
    <div class="rule" />

    <div class="body">
      <!-- Upload zone -->
      <UploadZone @files="handleFiles" />

      <div class="rule rule--inset" />

      <!-- Queue section -->
      <div class="queue-section">
        <div class="queue-meta">
          <span class="queue-label">UPLOAD QUEUE</span>
          <span class="queue-count">
            {{ files.length }}&nbsp;FILE{{ files.length !== 1 ? 'S' : '' }}
          </span>
        </div>

        <UploadQueue :files="files" @remove="removeFile" />

        <div class="actions">
          <button class="btn" :disabled="!hasCompleted" @click="clearCompleted">
            CLEAR COMPLETED
          </button>
          <button class="btn btn--primary" :disabled="!hasQueued" @click="uploadAll">
            UPLOAD ALL
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

/* ── Header ── */
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

/* ── Dividers ── */
.rule {
  height: 1px;
  background: var(--border);
}

.rule--inset {
  margin: 28px 0 0;
}

/* ── Body ── */
.body {
  padding: 28px 32px 40px;
  display: flex;
  flex-direction: column;
}

/* ── Queue section ── */
.queue-section {
  margin-top: 28px;
}

.queue-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0;
  padding: 0 0 10px;
  border-bottom: 1px solid var(--border);
}

.queue-label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--text-secondary);
}

.queue-count {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.07em;
  color: var(--text-muted);
}

/* ── Actions ── */
.actions {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}

.btn {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.09em;
  color: var(--text-secondary);
  background: none;
  border: 1px solid var(--border);
  padding: 7px 16px;
  cursor: pointer;
  transition: border-color 0.1s, color 0.1s;
}

.btn:hover:not(:disabled) {
  border-color: var(--text-secondary);
  color: var(--text-primary);
}

.btn:disabled {
  opacity: 0.25;
  cursor: not-allowed;
}

.btn--primary {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.btn--primary:hover:not(:disabled) {
  background: rgba(74, 127, 165, 0.08);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}
</style>
