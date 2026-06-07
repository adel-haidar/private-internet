<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { OAUTH_BASE, REDIRECT_URI } from '../config/env'
import { initiateLogin } from '../composables/useAuth'

const router       = useRouter()
const errorMessage = ref('')
const processing   = ref(true)

onMounted(async () => {
  const params = new URLSearchParams(window.location.search)
  const code             = params.get('code')
  const stateParam       = params.get('state')
  const errorParam       = params.get('error')
  const errorDescription = params.get('error_description')

  if (errorParam) {
    fail(errorDescription ?? errorParam)
    return
  }

  const storedState    = sessionStorage.getItem('adel_pkce_state')
  const codeVerifier   = sessionStorage.getItem('adel_pkce_verifier')
  const storedClientId = localStorage.getItem('adel_client_id')

  if (!stateParam || stateParam !== storedState) {
    fail('STATE_MISMATCH — possible CSRF')
    return
  }

  if (!codeVerifier) {
    fail('VERIFIER_MISSING')
    return
  }

  if (!code) {
    fail('CODE_MISSING')
    return
  }

  if (!storedClientId) {
    fail('CLIENT_ID_MISSING')
    return
  }

  try {
    const res = await fetch(`${OAUTH_BASE}/api/oauth/token`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body:    new URLSearchParams({
        grant_type:    'authorization_code',
        code,
        redirect_uri:  REDIRECT_URI,
        client_id:     storedClientId,
        code_verifier: codeVerifier,
      }),
    })

    if (!res.ok) {
      let detail = res.statusText
      try {
        const body = await res.json() as { detail?: string; error_description?: string }
        detail = body.detail ?? body.error_description ?? detail
      } catch {}
      fail(detail)
      return
    }

    const data = await res.json() as {
      access_token:  string
      refresh_token: string
      expires_in:    number
    }

    localStorage.setItem('adel_access_token',     data.access_token)
    localStorage.setItem('adel_refresh_token',    data.refresh_token)
    localStorage.setItem('adel_token_expires_at', String(Date.now() + data.expires_in * 1000))

    sessionStorage.removeItem('adel_pkce_verifier')
    sessionStorage.removeItem('adel_pkce_state')

    const intendedRoute = sessionStorage.getItem('adel_post_login_route') ?? '/'
    sessionStorage.removeItem('adel_post_login_route')

    router.replace(intendedRoute)
  } catch (e) {
    fail((e as Error).message ?? 'Unexpected error during token exchange')
  }
})

function fail(msg: string) {
  errorMessage.value = msg
  processing.value   = false
}

async function retry() {
  processing.value   = true
  errorMessage.value = ''
  await initiateLogin('/')
  // Hard redirect — line below is unreachable.
  processing.value = false
}
</script>

<template>
  <div class="callback">

    <!-- Processing state -->
    <div v-if="processing" class="status-wrap">
      <div class="spinner" />
      <div class="status-label mono">AUTHENTICATING...</div>
    </div>

    <!-- Error state -->
    <div v-else class="error-wrap">
      <div class="error-panel">
        <span class="br tl"></span>
        <span class="br tr"></span>
        <span class="br bl"></span>
        <span class="br br2"></span>

        <div class="error-head mono">AUTHENTICATION FAILED</div>
        <div class="error-code mono">{{ errorMessage }}</div>
        <button class="btn btn-primary retry-btn" @click="retry">RETRY</button>
      </div>
    </div>

  </div>
</template>

<style scoped>
.callback {
  height: 100vh;
  display: grid;
  place-items: center;
  background: var(--bg-base);
}

/* --- processing --- */
.status-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}
.spinner {
  width: 48px;
  height: 48px;
  border: 1px solid var(--border);
  animation: spinnerPulse 1.4s ease-in-out infinite;
}
@keyframes spinnerPulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.2; }
}
.status-label {
  font-size: 10px;
  letter-spacing: 0.2em;
  color: var(--text-2);
  text-transform: uppercase;
}

/* --- error --- */
.error-wrap {
  display: grid;
  place-items: center;
  padding: 32px;
}
.error-panel {
  width: min(440px, 100%);
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 28px 28px 32px;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.br { position: absolute; width: 10px; height: 10px; }
.br.tl  { top: -1px;    left: -1px;  border-top:    1px solid var(--danger); border-left:  1px solid var(--danger); }
.br.tr  { top: -1px;    right: -1px; border-top:    1px solid var(--danger); border-right: 1px solid var(--danger); }
.br.bl  { bottom: -1px; left: -1px;  border-bottom: 1px solid var(--danger); border-left:  1px solid var(--danger); }
.br.br2 { bottom: -1px; right: -1px; border-bottom: 1px solid var(--danger); border-right: 1px solid var(--danger); }

.error-head {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  color: var(--text-1);
  text-transform: uppercase;
}
.error-code {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--danger);
  word-break: break-all;
  padding: 8px 10px;
  border: 1px solid var(--danger);
  background: rgba(122, 58, 58, 0.08);
}
.retry-btn {
  align-self: flex-start;
  margin-top: 4px;
}
</style>
