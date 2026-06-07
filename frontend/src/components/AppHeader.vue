<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { NAV, SETTINGS, ICONS } from '../data/nav'
import { logout } from '../composables/useAuth'

const route = useRoute()
const all = [...NAV, SETTINGS]

const current = computed(() => {
  const m = all.find(n => '/' + n.name === route.path)
  return m ? m.label.toUpperCase() : '—'
})
const code = computed(() => {
  const m = all.find(n => '/' + n.name === route.path)
  return m ? m.idx : '00'
})
const logoutIcon = ICONS.logout
</script>

<template>
  <header class="header">
    <div class="header-left">
      <span class="header-brand">ADEL-INTELLIGENCE</span>
      <span class="header-vrule"></span>
      <span class="header-section mono">SEC {{ code }} / <b>{{ current }}</b></span>
    </div>
    <div class="header-right">
      <span class="conn"><span class="conn-dot"></span>UPLINK ACTIVE</span>
      <div class="user">
        <span class="user-name">ADEL HAIDAR</span>
        <button class="icon-btn" title="Terminate session" aria-label="Logout" @click="logout">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" v-html="logoutIcon"></svg>
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header {
  height: var(--header-h);
  flex: 0 0 auto;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--gutter);
}
.header-left { display: flex; align-items: center; gap: 16px; }
.header-brand {
  font-size: 12px; font-weight: 700; letter-spacing: 0.16em;
  color: var(--text-1); white-space: nowrap;
}
.header-vrule { width: 1px; height: 20px; background: var(--border); }
.header-section {
  font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.1em;
  color: var(--text-2); text-transform: uppercase;
}
.header-section b { color: var(--accent); font-weight: 500; }

.header-right { display: flex; align-items: center; gap: 16px; }
.conn {
  display: flex; align-items: center; gap: 7px;
  font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.1em;
  color: var(--text-2); text-transform: uppercase;
}
.conn-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--success);
  animation: connPulse 2.6s ease-out infinite;
}
@keyframes connPulse {
  0%   { box-shadow: 0 0 0 0 rgba(58,122,90,0.5); }
  70%  { box-shadow: 0 0 0 5px rgba(58,122,90,0); }
  100% { box-shadow: 0 0 0 0 rgba(58,122,90,0); }
}
.user {
  display: flex; align-items: center; gap: 9px;
  padding-left: 16px; border-left: 1px solid var(--border);
}
.user-name {
  font-size: 11px; font-weight: 600; letter-spacing: 0.1em;
  color: var(--text-1); text-transform: uppercase; white-space: nowrap;
}
.icon-btn {
  width: 28px; height: 28px;
  display: grid; place-items: center;
  background: transparent; border: 1px solid var(--border);
  color: var(--text-2); cursor: pointer;
  transition: color 0.12s, border-color 0.12s, background 0.12s;
}
.icon-btn:hover { color: var(--danger); border-color: var(--danger); }
.icon-btn svg { width: 14px; height: 14px; }

@media (max-width: 620px) {
  .header-brand, .header-vrule, .user-name { display: none; }
}
@media (prefers-reduced-motion: reduce) { .conn-dot { animation: none; } }
</style>
