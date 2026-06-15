<script setup lang="ts">
import PIIcon from './PIIcon.vue'

defineProps<{ module: string }>()

const bars = [0.3, 0.55, 0.8, 0.45, 0.9, 0.65, 0.4, 0.7, 0.5, 0.85, 0.6, 0.35, 0.75, 0.5, 0.65, 0.4]
const scenes = ['#1a2a3a', '#2a1a2e', '#1a2e22', '#2e2a1a', '#22203a', '#2e1a1a']
const posters = [
  { g: 'linear-gradient(160deg,#2a1a2e,#4a2a3e)', t: 'The Cartographer', m: '32 min' },
  { g: 'linear-gradient(160deg,#1a2a3a,#2a3a4a)', t: 'Northwind', m: 'S1 · E3' },
  { g: 'linear-gradient(160deg,#2e2616,#3e3420)', t: 'Slow Light', m: '18 min' },
]
const pulseItems = [
  { tone: 'informative', tag: 'Analysis', title: 'The quiet case for owning your own compute', meta: '6 min · from 3 memories' },
  { tone: 'critical', tag: 'Essay', title: 'Why convenience keeps winning the privacy debate', meta: '4 min · from 5 memories' },
]
const healthRows = [
  { kind: 'good', label: 'Recovery', text: 'You slept well. Your body is ready for a hard day.' },
  { kind: 'watch', label: 'Strain', text: 'Three intense days in a row — consider easing off.' },
]
const kindColor: Record<string,string> = { good: 'var(--success)', watch: 'var(--warning)', attention: 'var(--danger)' }
const segs = [
  { label: 'Housing', v: 38, c: 'var(--accent-primary)' },
  { label: 'Food', v: 22, c: 'var(--brain-amber)' },
  { label: 'Transport', v: 14, c: 'var(--success)' },
  { label: 'Other', v: 26, c: 'var(--border-medium)' },
]
</script>

<template>
  <!-- PULSE -->
  <div v-if="module === 'pulse'" class="pv-card pv-shadow" style="display:flex;flex-direction:column;gap:var(--space-3)">
    <div style="display:flex;align-items:center;justify-content:space-between">
      <span class="mk-pill">PULSE</span>
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary)">Today · 8 new</span>
    </div>
    <div v-for="(it, i) in pulseItems" :key="i" style="background:var(--background-raised);border-radius:var(--radius-sm);padding:var(--space-4)">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span :class="`pi-tone pi-tone--${it.tone}`" style="display:inline-flex;align-items:center;gap:4px;font-size:11px;padding:2px 8px;border-radius:999px">
          <span class="pi-tone__dot" />{{ it.tone }}
        </span>
        <span style="font-family:var(--font-mono);font-size:10px;color:var(--text-tertiary)">{{ it.tag }}</span>
      </div>
      <div style="font-family:var(--font-display);font-weight:600;font-size:15px;color:var(--text-primary);line-height:1.3">{{ it.title }}</div>
      <div style="font-size:12px;color:var(--text-tertiary);margin-top:6px">{{ it.meta }}</div>
    </div>
  </div>

  <!-- SIGNAL -->
  <div v-else-if="module === 'signal'" class="pv-card pv-shadow">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-4)">
      <span class="mk-pill">SIGNAL</span>
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary)">2:14</span>
    </div>
    <div style="position:relative;aspect-ratio:16/9;border-radius:var(--radius-sm);overflow:hidden;background:linear-gradient(135deg,#1a2a3a,#2a1a2e);display:flex;align-items:center;justify-content:center">
      <span style="width:46px;height:46px;border-radius:50%;background:color-mix(in srgb,#fff 16%,transparent);display:flex;align-items:center;justify-content:center;color:#fff">
        <PIIcon name="play" :size="18" />
      </span>
      <span style="position:absolute;inset-inline-start:10px;inset-block-end:10px;font-family:var(--font-mono);font-size:10px;color:rgba(255,255,255,0.8)">Scene 4 / 28</span>
    </div>
    <div style="display:flex;gap:5px;margin-top:var(--space-3)">
      <span v-for="(c, i) in scenes" :key="i" :style="{ flex:'1', height:'26px', borderRadius:'4px', background:c, opacity: i===3 ? 1 : 0.55, outline: i===3 ? '1.5px solid var(--brain-amber)' : 'none' }" />
    </div>
  </div>

  <!-- STORIES -->
  <div v-else-if="module === 'stories'" class="pv-card pv-shadow">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-4)">
      <span class="mk-pill">STORIES</span>
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary)">Continue watching</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:var(--space-3)">
      <div v-for="(p, i) in posters" :key="i">
        <div :style="{ aspectRatio:'2/3', borderRadius:'var(--radius-sm)', background:p.g, position:'relative', overflow:'hidden', display:'flex', alignItems:'flex-end', padding:'8px' }">
          <span v-if="i===0" style="position:absolute;inset-block-end:0;inset-inline-start:0;width:64%;height:3px;background:var(--brain-amber)" />
          <span style="font-family:var(--font-display);font-weight:600;font-size:11px;color:#fff;line-height:1.2">{{ p.t }}</span>
        </div>
        <div style="font-family:var(--font-mono);font-size:10px;color:var(--text-tertiary);margin-top:5px">{{ p.m }}</div>
      </div>
    </div>
  </div>

  <!-- ARIA -->
  <div v-else-if="module === 'aria'" class="pv-card pv-shadow">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-4)">
      <span class="mk-pill">ARIA</span>
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary)">Calm · evening</span>
    </div>
    <div style="display:flex;align-items:center;gap:var(--space-4)">
      <div style="width:56px;height:56px;border-radius:var(--radius-sm);background:linear-gradient(135deg,#a07ac9,#6ab0a0);flex:0 0 auto" />
      <div style="min-width:0">
        <div style="font-family:var(--font-display);font-weight:600;font-size:14px;color:var(--text-primary)">Tidewater, pt. II</div>
        <div style="font-size:12px;color:var(--text-tertiary)">Composed from 7 memories</div>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:2px;height:40px;margin-top:var(--space-4)">
      <span v-for="(b, i) in bars" :key="i" :style="{ flex:'1', height:(b*100)+'%', borderRadius:'2px', background: i<6 ? 'var(--accent-primary)' : 'var(--border-medium)' }" />
    </div>
    <div style="display:flex;align-items:center;justify-content:center;gap:var(--space-5);margin-top:var(--space-4);color:var(--text-secondary)">
      <PIIcon name="prev" :size="16" />
      <span style="width:40px;height:40px;border-radius:50%;background:var(--accent-primary);color:#fff;display:flex;align-items:center;justify-content:center">
        <PIIcon name="pause" :size="16" />
      </span>
      <PIIcon name="next" :size="16" />
    </div>
  </div>

  <!-- HEALTH -->
  <div v-else-if="module === 'health'" class="pv-card pv-shadow">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-4)">
      <span class="mk-pill" style="background:var(--success-surface);color:var(--success)">HEALTH</span>
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary)">Apple Watch · synced</span>
    </div>
    <div style="display:flex;flex-direction:column;gap:var(--space-3)">
      <div v-for="(r, i) in healthRows" :key="i" style="background:var(--background-raised);border-radius:var(--radius-sm);padding:var(--space-4)">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
          <span :style="{ width:'7px', height:'7px', borderRadius:'50%', background:kindColor[r.kind] }" />
          <span style="font-size:12px;font-weight:600;color:var(--text-primary)">{{ r.label }}</span>
        </div>
        <div class="t-serif" style="font-size:14px;color:var(--text-secondary);line-height:1.5">{{ r.text }}</div>
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;padding-inline:4px">
        <span style="font-size:12px;color:var(--text-tertiary)">Resting HR</span>
        <span style="font-family:var(--font-mono);font-size:14px;color:var(--text-primary)">54 bpm</span>
      </div>
    </div>
  </div>

  <!-- FINANCES -->
  <div v-else-if="module === 'finances'" class="pv-card pv-shadow">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-4)">
      <span class="mk-pill" style="background:var(--brain-amber-surface);color:var(--brain-amber)">FINANCES</span>
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary)">March · analysed locally</span>
    </div>
    <div class="t-serif" style="font-size:15px;color:var(--text-secondary);line-height:1.55;margin-bottom:var(--space-4)">
      Spending fell 8% versus February. Subscriptions are your fastest-growing category — worth a look.
    </div>
    <div style="display:flex;height:10px;border-radius:999px;overflow:hidden">
      <span v-for="(s, i) in segs" :key="i" :style="{ width:s.v+'%', background:s.c }" />
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:var(--space-3);margin-top:var(--space-3)">
      <span v-for="(s, i) in segs" :key="i" style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-secondary)">
        <span :style="{ width:'8px', height:'8px', borderRadius:'2px', background:s.c }" />
        {{ s.label }} <span style="font-family:var(--font-mono);color:var(--text-tertiary)">{{ s.v }}%</span>
      </span>
    </div>
  </div>
</template>
