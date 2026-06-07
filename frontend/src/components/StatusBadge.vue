<script setup lang="ts">
import { computed } from 'vue'

type Status = 'queued' | 'uploading' | 'success' | 'error'

const props = defineProps<{ status: Status }>()

const label = computed((): string => {
  const map: Record<Status, string> = {
    queued:    'STANDBY',
    uploading: 'PROCESSING',
    success:   'INDEXED',
    error:     'ERROR',
  }
  return map[props.status]
})
</script>

<template>
  <span class="badge" :class="status">{{ label }}</span>
</template>

<style scoped>
.badge {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.1em;
  padding: 2px 5px;
  border: 1px solid;
  white-space: nowrap;
  flex-shrink: 0;
}

.queued    { color: var(--status-standby);    border-color: var(--status-standby);    }
.uploading { color: var(--status-processing); border-color: var(--status-processing); }
.success   { color: var(--status-active);     border-color: var(--status-active);     }
.error     { color: var(--status-error);      border-color: var(--status-error);      }
</style>
