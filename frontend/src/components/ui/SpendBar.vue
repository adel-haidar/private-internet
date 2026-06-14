<script lang="ts">
export interface SpendSegment {
  label: string
  pct: number
  color: string
}
</script>

<script setup lang="ts">
interface Props {
  segments: SpendSegment[]
}
defineProps<Props>()
</script>

<template>
  <div>
    <div class="pi-spend">
      <div
        v-for="s in segments"
        :key="s.label"
        class="pi-spend__seg"
        :style="{ width: `${s.pct}%`, background: s.color }"
      />
    </div>
    <div class="pi-spend-legend">
      <span v-for="s in segments" :key="s.label" class="pi-spend-legend__i">
        <span class="pi-spend-legend__sw" :style="{ background: s.color }" />
        {{ s.label }} <span class="pi-spend-legend__pct">{{ s.pct }}%</span>
      </span>
    </div>
  </div>
</template>
