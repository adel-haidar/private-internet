<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterView } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import AppHeader from './components/AppHeader.vue'
import BootSequence from './components/BootSequence.vue'
import { isAuthenticated, hasRefreshToken, refreshTokens } from './composables/useAuth'

const route = useRoute()
const isPublic = computed(() => !!route.meta.public)

const booting = ref(sessionStorage.getItem('pi_booted') !== '1')
function bootDone() {
  booting.value = false
  sessionStorage.setItem('pi_booted', '1')
}

onMounted(async () => {
  if (!isAuthenticated() && hasRefreshToken()) {
    try { await refreshTokens() } catch { /* router guard handles the redirect */ }
  }
})
</script>

<template>
  <RouterView v-if="isPublic" />
  <div v-else class="shell">
    <Sidebar />
    <div class="main">
      <AppHeader />
      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>

  <BootSequence v-if="booting" @done="bootDone" />
  <div class="scanlines"></div>
  <div class="scan-sweep"></div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  height: 100svh;
  overflow: hidden;
  background: var(--bg-base);
}
.main { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.content {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: var(--gutter);
  min-height: 0;
  position: relative;
}

@media (max-width: 900px) {
  .shell { grid-template-columns: 64px 1fr; }
}
</style>
