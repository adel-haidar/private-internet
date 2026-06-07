<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

const emit = defineEmits<{ done: [] }>()

const lines = ref<string[]>([])
const finished = ref(false)

const script = [
  'PERSONAL-INTELLIGENCE :: secure command interface',
  'INITIALIZING SESSION ............ <span class="ok">OK</span>',
  'AUTH OPERATOR // ADEL HAIDAR .... <span class="ok">GRANTED</span>',
  'MOUNTING MODULES [07] ........... <span class="ac">LOADED</span>',
  'ESTABLISHING UPLINK ............. <span class="ok">CONNECTED</span>',
  'CLEARANCE LEVEL ................. <span class="ac">PRIMARY</span>',
]

let i = 0
let timer: ReturnType<typeof setTimeout> | null = null

function step() {
  if (i < script.length) {
    lines.value.push(script[i]); i++
    timer = setTimeout(step, 240 + Math.random() * 120)
  } else {
    finished.value = true
    timer = setTimeout(() => emit('done'), 520)
  }
}

function skip() {
  if (timer) clearTimeout(timer)
  emit('done')
}

onMounted(() => {
  step()
  window.addEventListener('keydown', skip, { once: true })
})
onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
  window.removeEventListener('keydown', skip)
})
</script>

<template>
  <div class="boot" @click="skip">
    <div class="boot-panel">
      <span class="br tl"></span><span class="br tr"></span>
      <span class="br bl"></span><span class="br br2"></span>
      <div class="boot-head">COMMAND INTERFACE<span class="v">// BOOT v3.1</span></div>
      <div class="boot-lines">
        <div class="boot-line" v-for="(l, idx) in lines" :key="idx">
          <span v-html="'> ' + l"></span>
        </div>
        <div class="boot-line" v-if="!finished">&gt; <span class="boot-cursor"></span></div>
        <div class="boot-line" v-else><span class="ac">&gt; ENTERING COMMAND CENTER</span></div>
      </div>
      <div class="boot-skip">[ PRESS ANY KEY OR CLICK TO SKIP ]</div>
    </div>
  </div>
</template>

<style scoped>
.boot {
  position: fixed; inset: 0; z-index: 200;
  background: var(--bg-base);
  display: flex; align-items: center; justify-content: center;
}
.boot-panel {
  width: min(560px, 86vw);
  border: 1px solid var(--border);
  background: var(--surface);
  padding: 28px 30px;
  position: relative;
}
.br { position: absolute; width: 12px; height: 12px; }
.br.tl  { top: -1px; left: -1px;  border-top: 1px solid var(--accent); border-left: 1px solid var(--accent); }
.br.tr  { top: -1px; right: -1px; border-top: 1px solid var(--accent); border-right: 1px solid var(--accent); }
.br.bl  { bottom: -1px; left: -1px;  border-bottom: 1px solid var(--accent); border-left: 1px solid var(--accent); }
.br.br2 { bottom: -1px; right: -1px; border-bottom: 1px solid var(--accent); border-right: 1px solid var(--accent); }

.boot-head {
  font-weight: 700; letter-spacing: 0.16em; font-size: 12px;
  color: var(--text-1); text-transform: uppercase;
  padding-bottom: 14px; margin-bottom: 16px;
  border-bottom: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center;
}
.boot-head .v { font-family: var(--font-mono); font-size: 9px; color: var(--accent-2); letter-spacing: 0.14em; }
.boot-lines { font-family: var(--font-mono); font-size: 11px; line-height: 1.9; min-height: 152px; }
.boot-line { color: var(--text-2); letter-spacing: 0.04em; }
.boot-line :deep(.ok) { color: var(--success); }
.boot-line :deep(.ac) { color: var(--accent); }
.boot-cursor {
  display: inline-block; width: 7px; height: 13px;
  background: var(--accent); vertical-align: middle;
  animation: blink 0.9s step-end infinite;
}
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.boot-skip {
  margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border);
  font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.14em;
  color: var(--text-3); text-transform: uppercase; text-align: center;
}
</style>
