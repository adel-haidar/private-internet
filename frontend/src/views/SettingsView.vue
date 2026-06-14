<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHead from '../components/ui/PageHead.vue'
import Avatar from '../components/ui/Avatar.vue'
import PiButton from '../components/ui/PiButton.vue'
import PiInput from '../components/ui/PiInput.vue'
import PiSelect from '../components/ui/PiSelect.vue'
import ModeToggle from '../components/ui/ModeToggle.vue'
import ConfirmModal from '../components/ui/ConfirmModal.vue'
import { useToast } from '../components/ui/useToast'
import { useTheme } from '../composables/useTheme'
import { useBilling } from '../composables/useBilling'
import { useBrainOrganiser } from '../composables/useBrainOrganiser'
import { requireAuth, logout } from '../composables/useAuth'
import { useI18n } from '../i18n'
import { API_BASE } from '../config/env'

const router = useRouter()
const toast = useToast()
const { theme } = useTheme()
const { t, locale, setLocale, locales } = useI18n()
const { status: billing, fetchStatus, openPortal } = useBilling()
const {
  status: organiserStatus,
  running: organiserRunning,
  organise: runOrganise,
  fetchStatus: fetchOrganiserStatus,
} = useBrainOrganiser()

// ── Sections (key drives state; label is translated) ─────────────────────────
const SECTIONS = [
  { key: 'profile', labelKey: 'settings.sections.profile' },
  { key: 'privacy', labelKey: 'settings.sections.privacy' },
  { key: 'notifications', labelKey: 'settings.sections.notifications' },
  { key: 'about', labelKey: 'settings.sections.about' },
] as const
type SectionKey = typeof SECTIONS[number]['key']
const section = ref<SectionKey>('profile')

// ── Profile ───────────────────────────────────────────────────────────────────
const email = ref('')
const displayName = ref('')
const originalName = ref('')
const savingProfile = ref(false)

const currentLangLabel = computed(() => locales.find(l => l.code === locale.value)?.label ?? 'English')

// Avatar
const avatarUrl = ref('')
const avatarInput = ref<HTMLInputElement | null>(null)
const uploadingAvatar = ref(false)

// Notification preferences (persisted; delivery activates with notifications)
const NOTIF_KEYS = ['pulse_posts', 'signal_ready', 'health_reminders', 'weekly_summary']
const notifPrefs = ref<Record<string, boolean>>({})

async function authHeaders(): Promise<Record<string, string>> {
  const token = await requireAuth()
  return { Authorization: `Bearer ${token}` }
}

onMounted(async () => {
  fetchStatus()
  fetchOrganiserStatus()
  try {
    const res = await fetch(`${API_BASE}/api/auth/me`, { headers: await authHeaders() })
    if (res.ok) {
      const { user } = await res.json()
      email.value = user.email ?? ''
      displayName.value = user.display_name ?? ''
      originalName.value = displayName.value
      avatarUrl.value = user.avatar_url ?? ''
      notifPrefs.value = user.notification_prefs ?? {}
    }
  } catch { /* ignore */ }
})

// ── Avatar upload ───────────────────────────────────────────────────────────────
function pickAvatar() { avatarInput.value?.click() }
async function onAvatarFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  uploadingAvatar.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${API_BASE}/api/auth/avatar`, { method: 'POST', headers: await authHeaders(), body: fd })
    const data = await res.json().catch(() => ({}))
    if (res.ok && data.avatar_url) { avatarUrl.value = data.avatar_url; toast(t('settings.toast.photoUpdated'), 'success') }
    else toast(data.error || t('settings.toast.photoError'), 'error')
  } catch { toast(t('settings.toast.photoError'), 'error') } finally { uploadingAvatar.value = false }
}

// ── Notification preferences ─────────────────────────────────────────────────────
async function toggleNotif(key: string) {
  notifPrefs.value = { ...notifPrefs.value, [key]: !notifPrefs.value[key] }
  try {
    await fetch(`${API_BASE}/api/auth/notifications`, {
      method: 'PATCH',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ prefs: notifPrefs.value }),
    })
  } catch { toast(t('settings.toast.prefError'), 'error') }
}

const nameDirty = computed(() => !!displayName.value.trim() && displayName.value !== originalName.value)

async function saveProfile() {
  savingProfile.value = true
  try {
    const res = await fetch(`${API_BASE}/api/auth/profile`, {
      method: 'PATCH',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: displayName.value.trim() }),
    })
    if (res.ok) { originalName.value = displayName.value.trim(); toast(t('settings.toast.profileUpdated'), 'success') }
    else toast(t('settings.toast.profileError'), 'error')
  } catch { toast(t('settings.toast.profileError'), 'error') } finally { savingProfile.value = false }
}

async function onLanguageChange(label: string) {
  const code = locales.find(l => l.label === label)?.code
  if (!code) return
  setLocale(code) // instant UI switch (+ <html> lang/dir)
  try {
    await fetch(`${API_BASE}/api/auth/profile`, {
      method: 'PATCH',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ language_preference: code }),
    })
    toast(t('settings.toast.languageUpdated'), 'success')
  } catch { /* best-effort */ }
}

// ── Privacy & data ──────────────────────────────────────────────────────────────
const organiserLastRunText = computed(() => {
  const lr = organiserStatus.value?.last_run
  if (!lr || !lr.completed_at) return t('settings.privacy.neverRun')
  return t('settings.privacy.lastRun', {
    date: new Date(lr.completed_at).toLocaleDateString(),
    dups: lr.duplicates_removed,
    merged: lr.clusters_merged,
  })
})

async function organiseNow() {
  const r = await runOrganise()
  if (r.ok || r.conflict) router.push('/memory')
  else toast(r.error || t('settings.toast.organiseError'), 'error')
}

const exporting = ref(false)
async function exportData() {
  exporting.value = true
  try {
    const res = await fetch(`${API_BASE}/api/auth/export`, { headers: await authHeaders() })
    if (!res.ok) throw new Error()
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'private-internet-export.json'
    a.click()
    URL.revokeObjectURL(url)
    toast(t('settings.toast.exportDownloaded'), 'success')
  } catch { toast(t('settings.toast.exportError'), 'error') } finally { exporting.value = false }
}

const confirmClear = ref(false)
async function clearBrain() {
  confirmClear.value = false
  try {
    const res = await fetch(`${API_BASE}/api/auth/clear-brain`, { method: 'POST', headers: await authHeaders() })
    if (res.ok) { const { deleted } = await res.json(); toast(t('settings.toast.cleared', { n: deleted }), 'warning') }
    else toast(t('settings.toast.clearError'), 'error')
  } catch { toast(t('settings.toast.clearError'), 'error') }
}

const delText = ref('')
const deleting = ref(false)
async function deleteAccount() {
  deleting.value = true
  try {
    const res = await fetch(`${API_BASE}/api/auth/account`, {
      method: 'DELETE',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm: 'DELETE' }),
    })
    if (res.ok) { toast(t('settings.toast.accountDeleted'), 'warning'); logout(); router.replace('/login') }
    else toast(t('settings.toast.accountError'), 'error')
  } catch { toast(t('settings.toast.accountError'), 'error') } finally { deleting.value = false }
}

const showBilling = computed(() => billing.value?.billing_enabled)
</script>

<template>
  <div style="max-width: var(--content-dashboard); margin: 0 auto;">
    <PageHead :title="t('settings.title')" :desc="t('settings.desc')" />

    <div class="pi-settings-grid" style="display: grid; grid-template-columns: 180px 1fr; gap: var(--space-8); align-items: start;">
      <nav style="display: flex; flex-direction: column; gap: 2px;">
        <button
          v-for="s in SECTIONS" :key="s.key"
          :style="{
            textAlign: 'left', padding: 'var(--space-2) var(--space-3)', borderRadius: 'var(--radius-sm)',
            fontSize: 'var(--text-sm)', fontFamily: 'var(--font-display)', fontWeight: 500, border: 'none', cursor: 'pointer',
            background: section === s.key ? 'var(--accent-surface)' : 'transparent',
            color: section === s.key ? 'var(--accent-hover)' : 'var(--text-secondary)',
          }"
          @click="section = s.key"
        >{{ t(s.labelKey) }}</button>
      </nav>

      <div>
        <!-- Profile -->
        <div v-if="section === 'profile'" style="display: flex; flex-direction: column; gap: var(--space-5); max-width: 460px;">
          <div style="display: flex; align-items: center; gap: var(--space-4);">
            <Avatar :name="displayName || email" :src="avatarUrl || undefined" :size="56" />
            <input ref="avatarInput" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="onAvatarFile" />
            <PiButton variant="secondary" size="compact" :loading="uploadingAvatar" @click="pickAvatar">{{ t('settings.profile.uploadPhoto') }}</PiButton>
          </div>

          <div class="pi-field">
            <label class="pi-label">{{ t('settings.profile.displayName') }}</label>
            <PiInput v-model="displayName" :placeholder="t('settings.profile.yourName')" />
          </div>
          <div>
            <PiButton variant="primary" size="compact" :disabled="!nameDirty" :loading="savingProfile" @click="saveProfile">{{ t('common.save') }}</PiButton>
          </div>

          <div class="pi-field">
            <label class="pi-label">{{ t('settings.profile.email') }}</label>
            <PiInput :modelValue="email" disabled />
            <span class="pi-field__hint">{{ t('settings.profile.readOnly') }}</span>
          </div>

          <div class="pi-field">
            <label class="pi-label">{{ t('settings.profile.language') }}</label>
            <PiSelect :options="locales.map(l => l.label)" :modelValue="currentLangLabel" @update:modelValue="onLanguageChange" />
          </div>

          <div>
            <div class="pi-label" style="margin-bottom: var(--space-2);">{{ t('settings.profile.appearance') }}</div>
            <div style="display: flex; align-items: center; gap: var(--space-3);">
              <ModeToggle />
              <span class="t-tertiary" style="font-size: var(--text-sm);">{{ t('settings.profile.currently', { theme }) }}</span>
            </div>
          </div>
        </div>

        <!-- Privacy & data -->
        <div v-else-if="section === 'privacy'" style="display: flex; flex-direction: column; max-width: 560px;">
          <div class="pi-set-row">
            <div>
              <div class="pi-set-row__title">{{ t('settings.privacy.exportTitle') }}</div>
              <div class="pi-set-row__desc">{{ t('settings.privacy.exportDesc') }}</div>
            </div>
            <PiButton variant="secondary" size="compact" icon="upload" :loading="exporting" @click="exportData">{{ t('settings.privacy.export') }}</PiButton>
          </div>

          <div class="pi-set-row">
            <div>
              <div class="pi-set-row__title" style="color: var(--warning);">{{ t('settings.privacy.clearTitle') }}</div>
              <div class="pi-set-row__desc">{{ t('settings.privacy.clearDesc') }}</div>
            </div>
            <PiButton variant="secondary" size="compact" style="border-color: var(--warning); color: var(--warning);" @click="confirmClear = true">{{ t('settings.privacy.clear') }}</PiButton>
          </div>

          <div class="pi-set-row">
            <div>
              <div class="pi-set-row__title">{{ t('settings.privacy.organiseTitle') }}</div>
              <div class="pi-set-row__desc">{{ t('settings.privacy.organiseDesc') }}</div>
              <div class="pi-set-row__desc t-mono" style="font-size: var(--text-xs); margin-top: 4px;">{{ organiserLastRunText }}</div>
            </div>
            <PiButton variant="secondary" size="compact" :loading="organiserRunning" :disabled="organiserRunning" @click="organiseNow">
              {{ t('settings.privacy.organiseNow') }}
            </PiButton>
          </div>

          <div v-if="showBilling" class="pi-set-row">
            <div>
              <div class="pi-set-row__title">{{ t('settings.privacy.subscriptionTitle') }}</div>
              <div class="pi-set-row__desc">{{ t('settings.privacy.subscriptionDesc') }}</div>
            </div>
            <PiButton variant="secondary" size="compact" @click="openPortal().catch(() => toast(t('settings.toast.noBilling'), 'error'))">{{ t('settings.privacy.manage') }}</PiButton>
          </div>

          <div class="pi-set-row">
            <div>
              <div class="pi-set-row__title" style="color: var(--danger);">{{ t('settings.privacy.deleteTitle') }}</div>
              <div class="pi-set-row__desc">{{ t('settings.privacy.deleteDesc') }}</div>
            </div>
            <div style="display: flex; gap: var(--space-2);">
              <PiInput v-model="delText" placeholder="DELETE" style="width: 120px;" />
              <PiButton variant="danger" size="compact" :disabled="delText !== 'DELETE'" :loading="deleting" @click="deleteAccount">{{ t('settings.privacy.delete') }}</PiButton>
            </div>
          </div>
        </div>

        <!-- Notifications -->
        <div v-else-if="section === 'notifications'" style="display: flex; flex-direction: column; gap: var(--space-4); max-width: 460px;">
          <label
            v-for="key in NOTIF_KEYS" :key="key"
            style="display: flex; align-items: center; justify-content: space-between; cursor: pointer; gap: var(--space-4);"
          >
            <span style="font-size: var(--text-base);">{{ t('settings.notif.' + key) }}</span>
            <button
              type="button"
              role="switch"
              :aria-checked="!!notifPrefs[key]"
              :class="['pi-switch', notifPrefs[key] ? 'pi-switch--on' : '']"
              @click="toggleNotif(key)"
            >
              <span class="pi-switch__knob" />
            </button>
          </label>
          <p class="t-tertiary" style="font-size: var(--text-xs); line-height: 1.5; margin-top: var(--space-2);">
            {{ t('settings.notif.note') }}
          </p>
        </div>

        <!-- About -->
        <div v-else style="display: flex; flex-direction: column; max-width: 460px;">
          <div class="pi-set-row">
            <div class="pi-set-row__title">{{ t('settings.about.version') }}</div>
            <span class="t-mono t-secondary" style="font-size: var(--text-sm);">4.0.0</span>
          </div>
          <div class="pi-set-row">
            <div class="pi-set-row__title">{{ t('settings.about.source') }}</div>
            <a href="https://github.com/adel-haidar/personal-intelligence" target="_blank" rel="noopener" style="font-size: var(--text-sm);">{{ t('settings.about.viewGithub') }}</a>
          </div>
          <div class="pi-set-row">
            <div>
              <div class="pi-set-row__title">{{ t('settings.about.hosting') }}</div>
              <div class="pi-set-row__desc">{{ t('settings.about.hostingDesc') }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <ConfirmModal
    :open="confirmClear" danger :confirmLabel="t('settings.privacy.clear')"
    :title="t('settings.confirmClearTitle')"
    :body="t('settings.confirmClearBody')"
    @close="confirmClear = false" @confirm="clearBrain"
  />
</template>

<style scoped>
.pi-set-row {
  display: flex; align-items: center; justify-content: space-between; gap: var(--space-4);
  padding: var(--space-3) 0; border-bottom: 1px solid var(--border-subtle);
}
.pi-set-row__title { font-family: var(--font-display); font-weight: 500; font-size: var(--text-base); color: var(--text-primary); }
.pi-set-row__desc { font-size: var(--text-sm); color: var(--text-secondary); margin-top: 2px; }

/* Toggle switch (notification preferences) */
.pi-switch {
  flex: 0 0 auto;
  width: 40px;
  height: 22px;
  border-radius: var(--radius-pill);
  background: var(--background-raised);
  border: 1px solid var(--border-medium);
  padding: 0;
  cursor: pointer;
  position: relative;
  transition: background 0.15s var(--ease), border-color 0.15s var(--ease);
}
.pi-switch__knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--text-tertiary);
  transition: transform 0.15s var(--ease), background 0.15s var(--ease);
}
.pi-switch--on {
  background: var(--accent-surface);
  border-color: var(--accent-primary);
}
.pi-switch--on .pi-switch__knob {
  transform: translateX(18px);
  background: var(--accent-primary);
}

/* RTL: knob travels the other way */
:global([dir='rtl']) .pi-switch__knob { left: auto; right: 2px; }
:global([dir='rtl']) .pi-switch--on .pi-switch__knob { transform: translateX(-18px); }

@media (max-width: 768px) {
  .pi-settings-grid { grid-template-columns: 1fr !important; }
}
</style>
