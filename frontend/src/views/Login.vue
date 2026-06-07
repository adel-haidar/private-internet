<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  initiateLogin,
  hasRefreshToken,
  refreshTokens,
  isAuthenticated,
} from '../composables/useAuth'

const router = useRouter()
const vRoute = useRoute()

const loading  = ref(false)
const resuming = ref(false)
const error    = ref('')
const hasSession = computed(() => hasRefreshToken())

const intendedRoute = computed(
  () => (vRoute.query.redirect as string | undefined) ?? '/'
)

onMounted(() => {
  // If somehow a fully valid token got us here, skip the login page
  if (isAuthenticated()) {
    router.replace(intendedRoute.value)
  }
})

async function handleLogin() {
  loading.value = true
  error.value   = ''
  try {
    await initiateLogin(intendedRoute.value)
    // Hard redirect happens inside initiateLogin — this line is never reached.
  } catch (e) {
    error.value   = (e as Error).message ?? 'Failed to start login'
    loading.value = false
  }
}

async function handleResume() {
  resuming.value = true
  error.value    = ''
  try {
    await refreshTokens()
    router.replace(intendedRoute.value)
  } catch (e) {
    error.value    = (e as Error).message ?? 'Session could not be resumed'
    resuming.value = false
  }
}
</script>

<template>
  <div class="login">
    <div class="panel">
      <span class="br tl"></span>
      <span class="br tr"></span>
      <span class="br bl"></span>
      <span class="br br2"></span>

      <div class="brand">PERSONAL-INTELLIGENCE</div>
      <div class="rule" />

      <div class="body">
        <div class="access-label mono">SECURE ACCESS REQUIRED</div>

        <p class="access-desc">
          Authentication via OAuth 2.1 + PKCE.<br />
          Your session is valid for 1 hour and auto-renews for 90 days.
        </p>

        <button
          class="btn btn-primary auth-btn"
          :disabled="loading || resuming"
          @click="handleLogin"
        >
          {{ loading ? 'REDIRECTING...' : 'AUTHENTICATE' }}
        </button>

        <div v-if="hasSession" class="resume-row">
          <span class="resume-text mono">Session token found.</span>
          <button
            class="resume-link mono"
            :disabled="resuming"
            @click="handleResume"
          >{{ resuming ? 'RESUMING...' : 'Resume session →' }}</button>
        </div>

        <div v-if="error" class="error-row mono">{{ error }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login {
  height: 100vh;
  display: grid;
  place-items: center;
  background: var(--bg-base);
  padding: 32px;
}

.panel {
  width: min(460px, 100%);
  background: var(--surface);
  border: 1px solid var(--border);
  position: relative;
}

/* corner brackets */
.br { position: absolute; width: 10px; height: 10px; }
.br.tl  { top: -1px;    left: -1px;  border-top:    1px solid var(--accent); border-left:  1px solid var(--accent); }
.br.tr  { top: -1px;    right: -1px; border-top:    1px solid var(--accent); border-right: 1px solid var(--accent); }
.br.bl  { bottom: -1px; left: -1px;  border-bottom: 1px solid var(--accent); border-left:  1px solid var(--accent); }
.br.br2 { bottom: -1px; right: -1px; border-bottom: 1px solid var(--accent); border-right: 1px solid var(--accent); }

.brand {
  padding: 22px 28px 20px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: var(--text-1);
  text-transform: uppercase;
}

.rule {
  height: 1px;
  background: var(--border);
}

.body {
  padding: 28px 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.access-label {
  font-size: 9px;
  letter-spacing: 0.18em;
  color: var(--text-3);
  text-transform: uppercase;
}

.access-desc {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-2);
}

.auth-btn {
  align-self: flex-start;
}
.auth-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.resume-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.resume-text {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--text-3);
}
.resume-link {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--accent);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.resume-link:hover { color: #7fb0cf; }
.resume-link:disabled { opacity: 0.4; cursor: not-allowed; }

.error-row {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--danger);
  border: 1px solid var(--danger);
  padding: 8px 10px;
  background: rgba(122, 58, 58, 0.08);
}
</style>
