<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  initiateLogin,
  hasRefreshToken,
  refreshTokens,
  isAuthenticated,
  loginWithPassword,
} from '../composables/useAuth'

const router  = useRouter()
const vRoute  = useRoute()

const email    = ref('')
const password = ref('')

const loading        = ref(false)
const oauthLoading   = ref(false)
const resuming       = ref(false)
const error          = ref('')
const hasSession     = computed(() => hasRefreshToken())
const forgotClicked  = ref(false)

const intendedRoute = computed(
  () => (vRoute.query.redirect as string | undefined) ?? '/'
)

onMounted(() => {
  if (isAuthenticated()) {
    router.replace(intendedRoute.value)
  }
})

async function handleLogin() {
  if (!email.value.trim() || !password.value) {
    error.value = 'Email and password are required.'
    return
  }
  loading.value = true
  error.value   = ''
  try {
    await loginWithPassword({ email: email.value.trim(), password: password.value })
    router.replace(intendedRoute.value)
  } catch (e) {
    error.value   = (e as Error).message ?? 'Login failed'
    loading.value = false
  }
}

async function handleOAuth() {
  oauthLoading.value = true
  error.value        = ''
  try {
    await initiateLogin(intendedRoute.value)
    // Hard redirect happens inside initiateLogin — never reached.
  } catch (e) {
    error.value        = (e as Error).message ?? 'Failed to start login'
    oauthLoading.value = false
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

function handleForgot(e: Event) {
  e.preventDefault()
  forgotClicked.value = true
}
</script>

<template>
  <div class="login">
    <div class="panel">
      <span class="br tl"></span>
      <span class="br tr"></span>
      <span class="br bl"></span>
      <span class="br br2"></span>

      <div class="brand">PRIVATE-INTERNET</div>
      <div class="rule" />

      <div class="body">
        <div class="access-label mono">CREDENTIAL ACCESS</div>

        <form class="form" @submit.prevent="handleLogin" novalidate>
          <div class="field">
            <label class="field-label mono" for="email">EMAIL ADDRESS</label>
            <input
              id="email"
              v-model="email"
              type="email"
              class="field-input mono"
              autocomplete="email"
              placeholder="user@domain.tld"
              :disabled="loading"
            />
          </div>

          <div class="field">
            <label class="field-label mono" for="password">PASSWORD</label>
            <input
              id="password"
              v-model="password"
              type="password"
              class="field-input mono"
              autocomplete="current-password"
              placeholder="••••••••••••"
              :disabled="loading"
            />
          </div>

          <div class="form-actions">
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="loading"
            >
              {{ loading ? 'AUTHENTICATING...' : 'LOG IN' }}
            </button>

            <a
              href="#"
              class="forgot-link mono"
              @click="handleForgot"
            >Forgot password</a>
          </div>

          <p v-if="forgotClicked" class="forgot-note mono">
            Password reset — coming soon.
          </p>
        </form>

        <div v-if="error" class="error-row mono">{{ error }}</div>

        <div class="divider">
          <span class="divider-line"></span>
          <span class="divider-label mono">OR</span>
          <span class="divider-line"></span>
        </div>

        <div class="oauth-row">
          <button
            class="btn btn-secondary oauth-btn"
            :disabled="oauthLoading || resuming"
            @click="handleOAuth"
          >
            {{ oauthLoading ? 'REDIRECTING...' : 'AUTHENTICATE VIA OAUTH 2.1' }}
          </button>
        </div>

        <div v-if="hasSession" class="resume-row">
          <span class="resume-text mono">Session token found.</span>
          <button
            class="resume-link mono"
            :disabled="resuming"
            @click="handleResume"
          >{{ resuming ? 'RESUMING...' : 'Resume session →' }}</button>
        </div>

        <div class="register-row mono">
          No account?
          <router-link to="/register" class="nav-link">Create one →</router-link>
        </div>
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

/* ---- form ---- */
.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-label {
  font-size: 9px;
  letter-spacing: 0.18em;
  color: var(--text-3);
  text-transform: uppercase;
}

.field-input {
  background: var(--bg-base);
  border: 1px solid var(--border);
  color: var(--text-1);
  font-family: var(--font-mono);
  font-size: 13px;
  padding: 8px 10px;
  outline: none;
  transition: border-color 0.12s;
  border-radius: 0;
  width: 100%;
}
.field-input::placeholder { color: var(--text-3); }
.field-input:focus { border-color: var(--accent); }
.field-input:disabled { opacity: 0.5; cursor: not-allowed; }

.form-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 2px;
}

.forgot-link {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--text-3);
  text-decoration: underline;
  text-underline-offset: 2px;
  cursor: pointer;
}
.forgot-link:hover { color: var(--text-2); }

.forgot-note {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--text-3);
  padding: 6px 10px;
  border: 1px solid var(--border);
  background: var(--bg-base);
}

/* ---- divider ---- */
.divider {
  display: flex;
  align-items: center;
  gap: 10px;
}
.divider-line {
  flex: 1;
  height: 1px;
  background: var(--border);
}
.divider-label {
  font-size: 9px;
  letter-spacing: 0.18em;
  color: var(--text-3);
}

/* ---- oauth ---- */
.oauth-btn { font-size: 11px; width: 100%; }
.oauth-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ---- session resume ---- */
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

/* ---- register link ---- */
.register-row {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--text-3);
}
.nav-link {
  color: var(--accent);
  text-decoration: underline;
  text-underline-offset: 2px;
  margin-left: 4px;
}
.nav-link:hover { color: #7fb0cf; }

/* ---- error ---- */
.error-row {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--danger);
  border: 1px solid var(--danger);
  padding: 8px 10px;
  background: rgba(122, 58, 58, 0.08);
}
</style>
