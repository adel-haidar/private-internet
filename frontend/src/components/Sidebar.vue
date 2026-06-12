<script setup lang="ts">
import { RouterLink } from 'vue-router'
import AppIcon from './AppIcon.vue'
import { NAV, SETTINGS } from '../data/nav'
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark"><span></span><span></span></div>
      <div class="brand-text">
        <div class="brand-word">PRIVATE-INTERNET</div>
        <div class="brand-sub">CMD//v3.1</div>
      </div>
    </div>

    <nav class="nav">
      <div class="nav-section-label">// MODULES</div>
      <RouterLink
        v-for="item in NAV"
        :key="item.name"
        class="nav-item"
        :to="'/' + item.name"
      >
        <span class="nav-index">{{ item.idx }}</span>
        <AppIcon :name="item.icon" />
        <span class="nav-label">{{ item.label }}</span>
        <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
      </RouterLink>

      <div class="nav-divider"></div>

      <div class="nav-section-label">// SYSTEM</div>
      <RouterLink class="nav-item" :to="'/' + SETTINGS.name">
        <span class="nav-index">{{ SETTINGS.idx }}</span>
        <AppIcon :name="SETTINGS.icon" />
        <span class="nav-label">{{ SETTINGS.label }}</span>
      </RouterLink>
    </nav>

    <div class="sidebar-foot">
      <span class="pulse-dot"></span>
      <span>SESSION SECURE</span>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-w);
  flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* brand */
.brand {
  height: var(--header-h);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 18px;
  border-bottom: 1px solid var(--border);
  flex: 0 0 auto;
}
.brand-mark {
  width: 22px; height: 22px;
  flex: 0 0 auto;
  border: 1px solid var(--accent);
  display: grid;
  grid-template-rows: 1fr 1fr;
  overflow: hidden;
}
.brand-mark span:first-child { background: var(--accent); }
.brand-mark span:last-child  { background: var(--accent-2); opacity: 0.85; }
.brand-word {
  font-size: 12px; font-weight: 700; letter-spacing: 0.14em;
  color: var(--text-1); white-space: nowrap;
}
.brand-sub {
  font-size: 9px; letter-spacing: 0.2em; color: var(--text-3);
  font-family: var(--font-mono); margin-top: 2px;
}

/* nav */
.nav {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 12px 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-height: 0;
}
.nav-section-label {
  font-size: 9px; letter-spacing: 0.22em; color: var(--text-3);
  font-family: var(--font-mono); padding: 6px 18px 8px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  height: 38px;
  padding: 0 16px;
  border-left: 2px solid transparent;
  color: var(--text-2);
  text-decoration: none;
  transition: background 0.12s ease, color 0.12s ease, border-color 0.12s ease;
  user-select: none;
}
.nav-item:hover { background: var(--elevated); color: var(--text-1); }
.nav-item.router-link-active {
  background: var(--elevated);
  color: var(--text-1);
  border-left-color: var(--accent);
}
.nav-item :deep(.app-icon) { stroke: currentColor; }
.nav-index {
  font-family: var(--font-mono); font-size: 9px;
  color: var(--text-3); width: 14px; flex: 0 0 auto;
}
.nav-item.router-link-active .nav-index { color: var(--accent); }
.nav-label {
  font-size: 11px; font-weight: 600; letter-spacing: 0.1em;
  text-transform: uppercase; white-space: nowrap; flex: 1 1 auto;
}
.nav-badge {
  font-family: var(--font-mono); font-size: 8px; letter-spacing: 0.08em;
  color: var(--accent-2); border: 1px solid var(--accent-2);
  padding: 1px 4px; line-height: 1.3; white-space: nowrap;
  opacity: 0.85; flex: 0 0 auto;
}

.nav-divider { height: 1px; background: var(--border); margin: 12px 18px; flex: 0 0 auto; }

/* footer */
.sidebar-foot {
  flex: 0 0 auto;
  border-top: 1px solid var(--border);
  padding: 10px 18px;
  display: flex; align-items: center; gap: 10px;
  font-family: var(--font-mono); font-size: 9px;
  color: var(--text-3); letter-spacing: 0.12em;
}
.pulse-dot {
  width: 6px; height: 6px; background: var(--success);
  flex: 0 0 auto; animation: dotPulse 2.4s ease-in-out infinite;
}
@keyframes dotPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

/* responsive — collapse to icon-only */
@media (max-width: 900px) {
  .sidebar { width: 64px; }
  .brand { justify-content: center; padding: 0; }
  .brand-text { display: none; }
  .nav-section-label { display: none; }
  .nav-item { justify-content: center; padding: 0; gap: 0; }
  .nav-index, .nav-label, .nav-badge { display: none; }
  .sidebar-foot { justify-content: center; padding: 10px 0; }
  .sidebar-foot span:last-child { display: none; }
}
@media (prefers-reduced-motion: reduce) { .pulse-dot { animation: none; } }
</style>
