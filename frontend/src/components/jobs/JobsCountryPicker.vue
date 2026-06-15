<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useJobsStore } from '../../composables/useJobsStore'

const store = useJobsStore()

const open = ref(false)
const filter = ref('')
const root = ref<HTMLElement | null>(null)

const filtered = computed(() => {
  const q = filter.value.trim().toLowerCase()
  const list = store.state.availableCountries
  if (!q) return list
  return list.filter(c => c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q))
})

const selectedCount = computed(() => store.state.selectedRunCountries.length)

const buttonLabel = computed(() => {
  const n = selectedCount.value
  if (n === 0) return 'Select countries'
  if (n === 1) {
    const code = store.state.selectedRunCountries[0]
    const match = store.state.availableCountries.find(c => c.code === code)
    return match?.name ?? code
  }
  return `${n} countries`
})

function isSelected(code: string): boolean {
  return store.state.selectedRunCountries.includes(code)
}

function toggle(code: string): void {
  store.toggleRunCountry(code)
}

function onDocClick(e: MouseEvent): void {
  if (root.value && !root.value.contains(e.target as Node)) open.value = false
}

onMounted(() => document.addEventListener('mousedown', onDocClick))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocClick))
</script>

<template>
  <div ref="root" class="country-picker">
    <button
      type="button"
      class="picker-btn"
      :class="{ active: selectedCount > 0 }"
      :aria-expanded="open"
      aria-haspopup="listbox"
      @click="open = !open"
    >
      <span class="picker-label">{{ buttonLabel }}</span>
      <span v-if="selectedCount > 1" class="picker-count">{{ selectedCount }}</span>
    </button>

    <div v-if="open" class="picker-panel" role="listbox">
      <input
        v-model="filter"
        type="text"
        class="picker-filter"
        placeholder="Filter countries…"
        aria-label="Filter countries"
        autofocus
      />
      <ul class="picker-list">
        <li v-if="filtered.length === 0" class="picker-empty">No matches</li>
        <li
          v-for="c in filtered"
          :key="c.code"
          class="picker-item"
          role="option"
          :aria-selected="isSelected(c.code)"
          @click="toggle(c.code)"
        >
          <span class="picker-check" :class="{ on: isSelected(c.code) }" aria-hidden="true">
            <svg v-if="isSelected(c.code)" width="11" height="9" viewBox="0 0 11 9" fill="none">
              <path d="M1 4.5L4 7.5L10 1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
          <span class="picker-name">{{ c.name }}</span>
          <span class="picker-code">{{ c.code }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.country-picker {
  position: relative;
}

.picker-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--background-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm, 8px);
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  padding: 7px 12px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.picker-btn:hover, .picker-btn[aria-expanded="true"] {
  border-color: var(--border-medium);
  color: var(--text-primary);
}
.picker-btn.active { color: var(--text-primary); }

.picker-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--accent-primary);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
}

.picker-panel {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 50;
  width: 260px;
  max-height: 320px;
  display: flex;
  flex-direction: column;
  background: var(--background-elevated, var(--background-surface));
  border: 1px solid var(--border-medium);
  border-radius: var(--radius-md, 10px);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28);
  overflow: hidden;
}

.picker-filter {
  margin: 8px;
  padding: 7px 10px;
  background: var(--background-base, var(--background-surface));
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm, 8px);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 13px;
}
.picker-filter:focus { outline: none; border-color: var(--accent-primary); }

.picker-list {
  list-style: none;
  margin: 0;
  padding: 0 4px 6px;
  overflow-y: auto;
}

.picker-empty {
  padding: 10px 12px;
  color: var(--text-tertiary, var(--text-secondary));
  font-size: 13px;
}

.picker-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 8px;
  border-radius: var(--radius-sm, 8px);
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
}
.picker-item:hover { background: var(--background-surface-hover, rgba(127,127,127,0.08)); color: var(--text-primary); }
.picker-item[aria-selected="true"] { color: var(--text-primary); }

.picker-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: 1px solid var(--border-medium);
  border-radius: 4px;
  color: #fff;
  flex-shrink: 0;
}
.picker-check.on { background: var(--accent-primary); border-color: var(--accent-primary); }

.picker-name { flex: 1; }
.picker-code {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-tertiary, var(--text-secondary));
  letter-spacing: 0.04em;
}
</style>
