<script setup lang="ts">
import BrainPulse from './BrainPulse.vue'

defineProps<{
  t: {
    memories: string
    updated: string
    health: string
    growing: string
    powers: string
  }
}>()

const mods = [
  { key: 'PULSE', v: 0.82, c: 'var(--accent-primary)' },
  { key: 'SIGNAL', v: 0.64, c: 'var(--brain-amber)' },
  { key: 'ARIA', v: 0.71, c: '#a07ac9' },
  { key: 'HEALTH', v: 0.55, c: 'var(--success)' },
]
</script>

<template>
  <div class="pv-card pv-shadow">
    <div style="display:flex;align-items:center;gap:var(--space-3)">
      <BrainPulse :size="32" />
      <div>
        <div style="font-family:var(--font-display);font-weight:600;font-size:15px;color:var(--text-primary)">{{ t.memories }}</div>
        <div style="font-size:12px;color:var(--text-tertiary)">{{ t.updated }}</div>
      </div>
    </div>
    <div style="margin-top:var(--space-5)">
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px">
        <span style="font-size:13px;color:var(--text-secondary)">{{ t.health }}</span>
        <span style="font-family:var(--font-mono);font-size:12px;color:var(--brain-amber)">{{ t.growing }} · 74%</span>
      </div>
      <div style="height:8px;border-radius:999px;background:var(--background-raised);overflow:hidden">
        <div style="width:74%;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--brain-amber),color-mix(in srgb,var(--brain-amber) 60%,var(--accent-primary)))" />
      </div>
    </div>
    <div style="margin-top:var(--space-5)">
      <div style="font-size:12px;color:var(--text-tertiary);margin-bottom:var(--space-3)">{{ t.powers }}</div>
      <div style="display:flex;flex-direction:column;gap:10px">
        <div v-for="m in mods" :key="m.key" style="display:grid;grid-template-columns:64px 1fr 34px;align-items:center;gap:var(--space-3)">
          <span style="font-family:var(--font-mono);font-size:10px;letter-spacing:0.08em;color:var(--text-secondary)">{{ m.key }}</span>
          <span style="height:5px;border-radius:999px;background:var(--background-raised);overflow:hidden;display:block">
            <span :style="{ display:'block', width:(m.v*100)+'%', height:'100%', borderRadius:'999px', background:m.c }" />
          </span>
          <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);text-align:end">{{ m.v.toFixed(2) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
