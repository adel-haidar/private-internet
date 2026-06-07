<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  idx: string
  title: string
  name: string
  status?: string
}>()

const ts = computed(() => new Date().toISOString().replace('T', ' ').slice(0, 19))
</script>

<template>
  <div class="grid12">
    <div class="section-head">
      <div class="section-stamp-wrap">
        <span class="br tl"></span><span class="br tr"></span>
        <span class="br bl"></span><span class="br br2"></span>
        <div class="section-code mono">[ SECTION {{ idx }} ]</div>
        <div class="section-title">{{ title }}</div>
      </div>
      <div class="section-meta">
        <div><span class="k">MODULE&nbsp;&nbsp;</span>{{ name.toUpperCase() }}.MOD</div>
        <div><span class="k">SYNC&nbsp;&nbsp;&nbsp;&nbsp;</span>{{ ts }}Z</div>
      </div>
    </div>

    <div class="stub">
      <div class="stub-inner">
        <div class="stub-ring"><span class="dot"></span></div>
        <div class="stub-label">Module Standby — No Data Stream</div>
        <div class="stub-sub">
          SECTION {{ idx }} — {{ title.toUpperCase() }} :: shell initialized.
          View scaffold registered. Awaiting module payload.
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.grid12 {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--gutter);
}

.section-head {
  grid-column: 1 / -1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
  margin-bottom: var(--gutter);
}
.section-stamp-wrap { position: relative; padding: 8px 14px; }
.br { position: absolute; width: 8px; height: 8px; }
.br.tl  { top: 0; left: 0;  border-top: 1px solid var(--accent); border-left: 1px solid var(--accent); }
.br.tr  { top: 0; right: 0; border-top: 1px solid var(--accent); border-right: 1px solid var(--accent); }
.br.bl  { bottom: 0; left: 0;  border-bottom: 1px solid var(--accent); border-left: 1px solid var(--accent); }
.br.br2 { bottom: 0; right: 0; border-bottom: 1px solid var(--accent); border-right: 1px solid var(--accent); }
.section-code {
  font-size: 10px; letter-spacing: 0.18em;
  color: var(--accent); margin-bottom: 4px;
}
.section-title {
  font-size: 17px; font-weight: 700; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--text-1); white-space: nowrap;
}
.section-meta {
  text-align: right; font-family: var(--font-mono); font-size: 10px;
  color: var(--text-2); letter-spacing: 0.08em; line-height: 1.9; padding-top: 4px;
}
.section-meta .k { color: var(--text-3); }

.stub {
  grid-column: 1 / -1;
  min-height: calc(100vh - var(--header-h) - 180px);
  display: flex; align-items: center; justify-content: center; text-align: center;
}
.stub-inner { display: flex; flex-direction: column; align-items: center; gap: 18px; }
.stub-ring {
  width: 64px; height: 64px; border: 1px solid var(--border);
  position: relative; display: grid; place-items: center;
}
.stub-ring::before, .stub-ring::after { content: ""; position: absolute; background: var(--border); }
.stub-ring::before { width: 1px; height: 100%; left: 50%; }
.stub-ring::after  { height: 1px; width: 100%; top: 50%; }
.stub-ring .dot { width: 6px; height: 6px; background: var(--text-3); position: relative; z-index: 1; }
.stub-label {
  font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.2em;
  color: var(--text-2); text-transform: uppercase;
}
.stub-sub {
  font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.12em;
  color: var(--text-3); max-width: 360px; line-height: 1.8;
}
</style>
