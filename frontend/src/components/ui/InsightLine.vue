<script setup lang="ts">
import StatusPill from './StatusPill.vue'

interface Props {
  kind?: 'good' | 'watch' | 'attention' | 'info'
  label: string
  text: string
  raw?: string
  showRaw?: boolean
}
withDefaults(defineProps<Props>(), { kind: 'info', showRaw: false })
</script>

<template>
  <div class="pi-iline">
    <div class="pi-iline__pill">
      <StatusPill :kind="kind">{{ label }}</StatusPill>
    </div>
    <div class="pi-iline__body">
      <div class="pi-iline__text">{{ text }}</div>
      <div v-if="showRaw && raw" class="pi-iline__raw">{{ raw }}</div>
    </div>
  </div>
</template>
