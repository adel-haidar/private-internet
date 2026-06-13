<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { registerWithPassword } from '../composables/useAuth'

const router = useRouter()

const email          = ref('')
const displayName    = ref('')
const password       = ref('')
const confirmPass    = ref('')
const referralSource = ref('')

const loading        = ref(false)
const error          = ref('')
const fieldErrors    = ref<Record<string, string>>({})

function validate(): boolean {
  const errs: Record<string, string> = {}

  if (!email.value.trim()) {
    errs.email = 'Email is required.'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())) {
    errs.email = 'Enter a valid email address.'
  }

  if (!displayName.value.trim()) {
    errs.displayName = 'Display name is required.'
  }

  if (!password.value) {
    errs.password = 'Password is required.'
  } else if (password.value.length < 12) {
    errs.password = 'Password must be at least 12 characters.'
  }

  if (!confirmPass.value) {
    errs.confirmPass = 'Please confirm your password.'
  } else if (password.value !== confirmPass.value) {
    errs.confirmPass = 'Passwords do not match.'
  }

  fieldErrors.value = errs
  return Object.keys(errs).length === 0
}

async function handleRegister() {
  error.value = ''
  if (!validate()) return

  loading.value = true
  try {
    await registerWithPassword({
      email:         email.value.trim(),
      display_name:  displayName.value.trim(),
      password:      password.value,
      ...(referralSource.value.trim()
        ? { referral_source: referralSource.value.trim() }
        : {}),
    })
    // TODO: redirect to /onboarding once Section 3 lands
    router.replace('/')
  } catch (e) {
    error.value   = (e as Error).message ?? 'Registration failed'
    loading.value = false
  }
}
</script>

<template>
  <div class="register">
    <div class="panel">
      <span class="br tl"></span>
      <span class="br tr"></span>
      <span class="br bl"></span>
      <span class="br br2"></span>

      <div class="brand">PRIVATE-INTERNET</div>
      <div class="rule" />

      <div class="body">
        <div class="access-label mono">NEW ACCOUNT REGISTRATION</div>

        <form class="form" @submit.prevent="handleRegister" novalidate>
          <div class="field">
            <label class="field-label mono" for="email">EMAIL ADDRESS</label>
            <input
              id="email"
              v-model="email"
              type="email"
              class="field-input mono"
              :class="{ 'field-input--error': fieldErrors.email }"
              autocomplete="email"
              placeholder="user@domain.tld"
              :disabled="loading"
            />
            <span v-if="fieldErrors.email" class="field-error mono">{{ fieldErrors.email }}</span>
          </div>

          <div class="field">
            <label class="field-label mono" for="display-name">DISPLAY NAME</label>
            <input
              id="display-name"
              v-model="displayName"
              type="text"
              class="field-input mono"
              :class="{ 'field-input--error': fieldErrors.displayName }"
              autocomplete="nickname"
              placeholder="Your name"
              :disabled="loading"
            />
            <span v-if="fieldErrors.displayName" class="field-error mono">{{ fieldErrors.displayName }}</span>
          </div>

          <div class="field">
            <label class="field-label mono" for="password">PASSWORD</label>
            <input
              id="password"
              v-model="password"
              type="password"
              class="field-input mono"
              :class="{ 'field-input--error': fieldErrors.password }"
              autocomplete="new-password"
              placeholder="Minimum 12 characters"
              :disabled="loading"
            />
            <span v-if="fieldErrors.password" class="field-error mono">{{ fieldErrors.password }}</span>
          </div>

          <div class="field">
            <label class="field-label mono" for="confirm-pass">CONFIRM PASSWORD</label>
            <input
              id="confirm-pass"
              v-model="confirmPass"
              type="password"
              class="field-input mono"
              :class="{ 'field-input--error': fieldErrors.confirmPass }"
              autocomplete="new-password"
              placeholder="Repeat password"
              :disabled="loading"
            />
            <span v-if="fieldErrors.confirmPass" class="field-error mono">{{ fieldErrors.confirmPass }}</span>
          </div>

          <div class="field">
            <label class="field-label mono" for="referral">HOW DID YOU HEAR ABOUT PRIVATE INTERNET? <span class="optional">(OPTIONAL)</span></label>
            <textarea
              id="referral"
              v-model="referralSource"
              class="field-textarea mono"
              rows="3"
              placeholder="e.g. a friend, Twitter/X, Hacker News…"
              :disabled="loading"
            />
          </div>

          <button
            type="submit"
            class="btn btn-primary submit-btn"
            :disabled="loading"
          >
            {{ loading ? 'REGISTERING...' : 'CREATE ACCOUNT' }}
          </button>
        </form>

        <div v-if="error" class="error-row mono">{{ error }}</div>

        <div class="login-row mono">
          Already have an account?
          <router-link to="/login" class="nav-link">Log in →</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: var(--bg-base);
  padding: 32px;
}

.panel {
  width: min(480px, 100%);
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
  gap: 20px;
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

.optional {
  color: var(--text-3);
  opacity: 0.6;
}

.field-input,
.field-textarea {
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
.field-textarea {
  resize: vertical;
  min-height: 68px;
  line-height: 1.5;
}
.field-input::placeholder,
.field-textarea::placeholder { color: var(--text-3); }
.field-input:focus,
.field-textarea:focus { border-color: var(--accent); }
.field-input:disabled,
.field-textarea:disabled { opacity: 0.5; cursor: not-allowed; }

.field-input--error { border-color: var(--danger) !important; }

.field-error {
  font-size: 10px;
  letter-spacing: 0.06em;
  color: var(--danger);
}

.submit-btn { width: 100%; margin-top: 4px; }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ---- error ---- */
.error-row {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--danger);
  border: 1px solid var(--danger);
  padding: 8px 10px;
  background: rgba(122, 58, 58, 0.08);
}

/* ---- login link ---- */
.login-row {
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
</style>
