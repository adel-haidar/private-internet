<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  files: [files: File[]]
}>()

const isDragOver = ref(false)
const inputRef   = ref<HTMLInputElement>()

function onDragEnter(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = true
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
}

function onDragLeave(e: DragEvent) {
  // Only clear when leaving the zone itself, not a child element
  if (!(e.currentTarget as Element).contains(e.relatedTarget as Node | null)) {
    isDragOver.value = false
  }
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false
  const dropped = Array.from(e.dataTransfer?.files ?? [])
  if (dropped.length) emit('files', dropped)
}

function onInputChange(e: Event) {
  const input    = e.target as HTMLInputElement
  const selected = Array.from(input.files ?? [])
  if (selected.length) emit('files', selected)
  input.value = '' // reset so same file can be re-selected
}
</script>

<template>
  <div
    class="zone"
    :class="{ 'drag-over': isDragOver }"
    role="button"
    tabindex="0"
    aria-label="Upload zone — click or drag files here"
    @click="inputRef?.click()"
    @keydown.enter="inputRef?.click()"
    @dragenter="onDragEnter"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <input ref="inputRef" type="file" multiple hidden @change="onInputChange" />

    <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
      <polyline points="12,4 12,16" stroke-linecap="square" />
      <polyline points="8,8 12,4 16,8"  stroke-linecap="square" stroke-linejoin="miter" />
      <line x1="4" y1="20" x2="20" y2="20" stroke-linecap="square" />
    </svg>

    <p class="label">DROP FILES HERE OR CLICK TO BROWSE</p>
    <p class="hint">PDF · TXT · MD · DOCX · CSV · JSON · PNG · JPG</p>
    <p class="hint">MAX 50 MB PER FILE</p>
  </div>
</template>

<style scoped>
.zone {
  padding: 52px 32px;
  border: 1px dashed var(--border);
  background: transparent;
  cursor: pointer;
  text-align: center;
  user-select: none;
  transition: border-color 0.12s, background 0.12s;
  outline: none;
}

.zone:hover,
.zone.drag-over {
  border-style: solid;
  border-color: var(--accent-primary);
  background: rgba(74, 127, 165, 0.04);
}

.zone:focus-visible {
  outline: 1px solid var(--accent-primary);
  outline-offset: -1px;
}

.icon {
  width: 28px;
  height: 28px;
  color: var(--text-muted);
  margin-bottom: 18px;
}

.zone.drag-over .icon {
  color: var(--accent-primary);
}

.label {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.09em;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.hint {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 4px;
}
</style>
