<script setup lang="ts">
import { ref } from 'vue'
import type { UploadFile } from '../composables/useFileUpload'
import StatusBadge from './StatusBadge.vue'

defineProps<{ files: UploadFile[] }>()

const emit = defineEmits<{
  remove: [id: string]
}>()

const expandedErrors = ref<string[]>([])

function toggleError(id: string, status: string) {
  if (status !== 'error') return
  const idx = expandedErrors.value.indexOf(id)
  if (idx !== -1) {
    expandedErrors.value.splice(idx, 1)
  } else {
    expandedErrors.value.push(id)
  }
}

function isExpanded(id: string): boolean {
  return expandedErrors.value.includes(id)
}

function fileExt(name: string): string {
  return (name.split('.').pop() ?? 'BIN').slice(0, 4).toUpperCase()
}

function formatSize(bytes: number): string {
  if (bytes < 1024)           return `${bytes}B`
  if (bytes < 1024 * 1024)    return `${Math.round(bytes / 1024)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}
</script>

<template>
  <div class="queue">
    <div v-if="files.length === 0" class="empty">
      NO FILES QUEUED
    </div>

    <div v-for="f in files" :key="f.id" class="row-wrap">
      <div
        class="row"
        :class="{ clickable: f.status === 'error' }"
        @click="toggleError(f.id, f.status)"
      >
        <!-- Extension badge -->
        <span class="ext">{{ fileExt(f.file.name) }}</span>

        <!-- Filename + server ID -->
        <div class="name-col">
          <span class="filename" :title="f.file.name">{{ f.file.name }}</span>
          <span
            v-if="f.status === 'success' && f.serverResponse"
            class="server-id"
            :title="f.serverResponse.id"
          >{{ f.serverResponse.id }}</span>
        </div>

        <!-- Progress (only while uploading) -->
        <div class="progress-col">
          <template v-if="f.status === 'uploading'">
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: `${f.progress}%` }" />
            </div>
            <span class="pct">{{ f.progress }}%</span>
          </template>
        </div>

        <!-- Size -->
        <span class="size">{{ formatSize(f.file.size) }}</span>

        <!-- Status badge -->
        <StatusBadge :status="f.status" />

        <!-- Remove -->
        <button
          class="remove"
          :aria-label="`Remove ${f.file.name}`"
          @click.stop="emit('remove', f.id)"
        >×</button>
      </div>

      <!-- Error detail (toggled by clicking error row) -->
      <div v-if="f.status === 'error' && isExpanded(f.id)" class="error-detail">
        {{ f.error ?? 'Unknown error' }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.queue {
  border: 1px solid var(--border);
  border-top: none;
}

.empty {
  padding: 28px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}

.row-wrap {
  border-top: 1px solid var(--border);
}

.row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 14px;
  min-height: 40px;
}

.row.clickable {
  cursor: pointer;
}

.row:hover .remove {
  opacity: 1;
}

/* Extension badge */
.ext {
  font-family: var(--font-mono);
  font-size: 8px;
  letter-spacing: 0.07em;
  color: var(--text-muted);
  border: 1px solid var(--border);
  padding: 1px 4px;
  min-width: 30px;
  text-align: center;
  flex-shrink: 0;
}

/* Filename column */
.name-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.filename {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.server-id {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-muted);
  letter-spacing: 0.03em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Progress column — fixed width regardless of state */
.progress-col {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 150px;
  flex-shrink: 0;
}

.progress-track {
  flex: 1;
  height: 2px;
  background: var(--border);
  position: relative;
  overflow: hidden;
}

.progress-fill {
  position: absolute;
  inset: 0 auto 0 0;
  height: 100%;
  background: var(--accent-primary);
  transition: width 0.1s linear;
}

.pct {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-muted);
  width: 30px;
  text-align: right;
  flex-shrink: 0;
}

/* Size */
.size {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-muted);
  width: 44px;
  text-align: right;
  flex-shrink: 0;
}

/* Remove button */
.remove {
  font-family: var(--font-mono);
  font-size: 14px;
  line-height: 1;
  color: var(--text-muted);
  background: none;
  border: none;
  padding: 0 2px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.1s, color 0.1s;
  flex-shrink: 0;
}

.remove:hover {
  color: var(--status-error);
  opacity: 1;
}

/* Error expansion */
.error-detail {
  padding: 8px 14px 10px 58px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--status-error);
  background: rgba(240, 68, 68, 0.05);
  border-top: 1px solid var(--border);
  word-break: break-all;
}
</style>
