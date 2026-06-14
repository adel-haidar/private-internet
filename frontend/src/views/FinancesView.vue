<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import PageHead from '../components/ui/PageHead.vue'
import PiCard from '../components/ui/PiCard.vue'
import PiButton from '../components/ui/PiButton.vue'
import PIIcon from '../components/ui/PIIcon.vue'
import UploadBanner from '../components/ui/UploadBanner.vue'
import InsightCard from '../components/ui/InsightCard.vue'
import StatusPill from '../components/ui/StatusPill.vue'
import SpendBar, { type SpendSegment } from '../components/ui/SpendBar.vue'
import ProgressBar from '../components/ui/ProgressBar.vue'
import ConfirmModal from '../components/ui/ConfirmModal.vue'
import { useBankAdviser } from '../composables/useBankAdviser'
import { requireAuth } from '../composables/useAuth'
import { API_BASE } from '../config/env'
import { useToast } from '../components/ui/useToast'

const { status, result, error, lastRun, runAnalysis, loadLatest } = useBankAdviser()
const toast = useToast()

onMounted(() => loadLatest())

const populated = computed(() => status.value === 'success' && !!result.value)
const SAVINGS_TARGET = 20

// ── Currency ──────────────────────────────────────────────────────────────────
const CURRENCY_SYMBOL: Record<string, string> = { EUR: '€', USD: '$', GBP: '£', CHF: 'CHF ' }
const sym = computed(() => CURRENCY_SYMBOL[result.value?.meta.currency ?? 'EUR'] ?? `${result.value?.meta.currency ?? ''} `)
function money(v: number): string { return `${sym.value}${Math.round(Math.abs(v)).toLocaleString()}` }

function prettyCategory(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// ── Spend breakdown ─────────────────────────────────────────────────────────
const SEG_COLORS = ['var(--accent-primary)', 'var(--success)', 'var(--brain-amber)', 'var(--border-strong)']

const spendSegments = computed<SpendSegment[]>(() => {
  const sa = result.value?.spending_analysis
  if (!sa) return []
  const entries = Object.entries(sa.categories)
    .map(([name, c]) => ({ name, actual: c.actual }))
    .filter(e => e.actual > 0)
    .sort((a, b) => b.actual - a.actual)
  const total = sa.total_expenses || entries.reduce((s, e) => s + e.actual, 0)
  if (!total) return []
  const top = entries.slice(0, 3)
  const restActual = entries.slice(3).reduce((s, e) => s + e.actual, 0)
  const segs: SpendSegment[] = top.map((e, i) => ({ label: prettyCategory(e.name), pct: Math.round((e.actual / total) * 100), color: SEG_COLORS[i] }))
  if (restActual > 0) segs.push({ label: 'Other', pct: Math.round((restActual / total) * 100), color: SEG_COLORS[3] })
  return segs
})

const monthDelta = computed<number | null>(() => {
  const mom = result.value?.spending_analysis.month_over_month
  if (!mom || Object.keys(mom).length === 0) return null
  return Object.values(mom).reduce((s, e) => s + e.delta_eur, 0)
})

const moneyLead = computed(() => {
  const d = monthDelta.value
  if (d == null) return 'Here is where your money went this month.'
  if (Math.abs(d) < 1) return 'Your spending was roughly flat compared with last month.'
  return d > 0
    ? `You spent ${money(d)} more than last month.`
    : `You spent ${money(d)} less than last month.`
})

// ── Savings & investments ────────────────────────────────────────────────────
const savingsRate = computed<number | null>(() => {
  const inc = result.value?.income_summary.total_income
  const net = result.value?.spending_analysis.net_savings_this_period
  if (!inc || net == null) return null
  return (net / inc) * 100
})
const savingsFill = computed(() => {
  if (savingsRate.value == null) return 0
  return Math.max(0, Math.min(100, (savingsRate.value / SAVINGS_TARGET) * 100))
})
const savingsStatus = computed<{ kind: 'good' | 'watch' | 'attention'; text: string }>(() => {
  const t = result.value?.yearly_progress.trajectory
  if (t === 'ahead') return { kind: 'good', text: 'Ahead' }
  if (t === 'behind') return { kind: 'attention', text: 'Behind' }
  return { kind: 'watch', text: 'On track' }
})
const investmentNote = computed(() => result.value?.investment_signal.note ?? '')

// ── Suggestions ──────────────────────────────────────────────────────────────
const suggestText = computed(() => {
  if (result.value?.reasoning) return result.value.reasoning
  const recs = result.value?.recommendations ?? []
  return recs.slice(0, 3).map(r => r.action).join(' ')
})

// ── Detailed chart (hbar) ────────────────────────────────────────────────────
const hbarRows = computed(() => {
  const pie = result.value?.chart_data.spending_by_category_pie
  let rows: { label: string; value: number }[] = []
  if (pie && pie.length) {
    rows = pie.map(p => ({ label: prettyCategory(p.label), value: p.value }))
  } else if (result.value) {
    rows = Object.entries(result.value.spending_analysis.categories)
      .map(([name, c]) => ({ label: prettyCategory(name), value: c.actual }))
  }
  return rows.filter(r => r.value > 0).sort((a, b) => b.value - a.value)
})
const hbarMax = computed(() => Math.max(1, ...hbarRows.value.map(r => r.value)))
const chartsOpen = ref(false)

// ── Run / upload ─────────────────────────────────────────────────────────────
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
function pickFile() { fileInput.value?.click() }

async function onPickFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  uploading.value = true
  try {
    const token = await requireAuth()
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${API_BASE}/api/file`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd })
    toast(res.ok ? 'File added — run analysis to see your summary' : 'Upload failed', res.ok ? 'success' : 'error')
  } catch {
    toast('Upload failed', 'error')
  } finally {
    uploading.value = false
  }
}

async function runNow() {
  await runAnalysis({ mode: 'ytd' })
  if (status.value === 'error') toast(error.value ?? 'Analysis failed', 'error')
}

const lastRunLabel = computed(() => lastRun.value ? lastRun.value.toLocaleDateString() : null)

// ── Delete ───────────────────────────────────────────────────────────────────
const confirmDel = ref(false)
async function deleteAll() {
  confirmDel.value = false
  // NOTE: backend DELETE endpoint for financial data is not implemented yet.
  try {
    const token = await requireAuth()
    const res = await fetch(`${API_BASE}/api/banking/data`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
    toast(res.ok ? 'Financial data deleted' : 'Deleting financial data isn’t available yet.', res.ok ? 'warning' : 'error')
  } catch {
    toast('Deleting financial data isn’t available yet.', 'error')
  }
}
</script>

<template>
  <div style="max-width: var(--content-dashboard); margin: 0 auto;">
    <PageHead
      title="Finances"
      desc="Upload your financial documents and your brain gives you a clear picture of your money — without the jargon."
    />

    <input ref="fileInput" type="file" accept=".pdf,.csv,.xlsx,.xls" hidden @change="onPickFile" />

    <!-- Loading -->
    <PiCard v-if="status === 'loading'" style="margin-bottom: var(--space-6);">
      <div class="pi-progress pi-progress--thin"><div class="pi-progress__track"><div class="pi-progress__fill" style="width: 40%;" /></div></div>
      <p class="t-secondary" style="font-size: var(--text-sm); margin-top: var(--space-3);">Analysing your statements…</p>
    </PiCard>

    <!-- Empty / first-run -->
    <UploadBanner
      v-if="!populated && status !== 'loading'"
      tone="info"
      icon="finances"
      title="Get your financial analysis"
      intro="Upload your financial documents and your brain will give you a clear picture of your money — without jargon."
      :items="[
        'Bank statements (PDF or CSV)',
        'Payslips or salary records',
        'Investment portfolio exports (PDF, CSV, or Excel)',
        'Credit card statements',
        'Pension or retirement fund summaries',
      ]"
      note="This data is only on your server. You can delete it at any time from Brain → Manage data."
    >
      <template #actions>
        <PiButton variant="cta" icon="upload" :loading="uploading" @click="pickFile">Upload financial files</PiButton>
        <PiButton variant="secondary" @click="runNow">Run analysis</PiButton>
      </template>
    </UploadBanner>

    <!-- Populated -->
    <template v-if="populated">
      <div class="pi-insight-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); margin-bottom: var(--space-4);">
        <!-- Your money this month (full width) -->
        <div style="grid-column: 1 / -1;">
          <InsightCard title="Your money this month">
            <SpendBar v-if="spendSegments.length" :segments="spendSegments" />
            <p class="pi-insight__lead" style="margin-top: var(--space-5);">{{ moneyLead }}</p>
          </InsightCard>
        </div>

        <!-- Savings & investments -->
        <InsightCard title="Savings and investments">
          <template #status><StatusPill :kind="savingsStatus.kind">{{ savingsStatus.text }}</StatusPill></template>
          <div v-if="savingsRate != null" class="pi-goal" style="margin-bottom: var(--space-4);">
            <div class="pi-goal__head">
              <span class="t-secondary" style="font-size: var(--text-sm);">Savings rate</span>
              <span class="pi-goal__val" style="color: var(--success);">{{ Math.round(savingsRate) }}%</span>
            </div>
            <ProgressBar :value="savingsFill" variant="success" :showPct="false" />
            <div class="pi-goal__scale"><span>0%</span><span>Target {{ SAVINGS_TARGET }}%</span></div>
          </div>
          <p v-if="savingsRate != null" class="pi-insight__lead" style="font-size: var(--text-base);">
            You're saving about {{ Math.round(savingsRate) }}% of your income. Most financial guidance suggests {{ SAVINGS_TARGET }}% — {{ savingsRate >= SAVINGS_TARGET ? "you're there." : "you're close, keep building the habit." }}
          </p>
          <p v-if="investmentNote" class="pi-insight__lead" style="font-size: var(--text-base); margin-top: var(--space-3); padding-top: var(--space-3); border-top: 1px solid var(--border-subtle);">
            {{ investmentNote }}
          </p>
        </InsightCard>

        <!-- What your finances suggest -->
        <InsightCard title="What your finances suggest">
          <p class="pi-insight__lead" style="font-size: var(--text-base);">{{ suggestText || 'No specific suggestions right now — your finances look balanced.' }}</p>
        </InsightCard>
      </div>

      <!-- Detailed charts — collapsed, horizontal bars only -->
      <PiCard style="margin-bottom: var(--space-6);">
        <div :class="['pi-collapse', chartsOpen ? 'pi-collapse--open' : '']">
          <button type="button" class="pi-collapse__toggle" :aria-expanded="chartsOpen" @click="chartsOpen = !chartsOpen">
            <PIIcon name="chevronRight" :size="14" />Show detailed charts
          </button>
          <div v-if="chartsOpen" class="pi-collapse__body">
            <div style="font-family: var(--font-display); font-weight: 500; margin-bottom: var(--space-4);">Spending by category · this period</div>
            <div class="pi-hbar">
              <div v-for="r in hbarRows" :key="r.label" class="pi-hbar__row">
                <span class="pi-hbar__label">{{ r.label }}</span>
                <div class="pi-hbar__track"><div class="pi-hbar__fill" :style="{ width: `${(r.value / hbarMax) * 100}%` }" /></div>
                <span class="pi-hbar__val">{{ money(r.value) }}</span>
              </div>
            </div>
          </div>
        </div>
      </PiCard>

      <!-- Actions -->
      <div style="display: flex; justify-content: space-between; gap: var(--space-3); flex-wrap: wrap; align-items: center;">
        <div style="display: flex; gap: var(--space-3); align-items: center; flex-wrap: wrap;">
          <PiButton variant="ghost" icon="plus" :loading="uploading" @click="pickFile">Upload more data</PiButton>
          <PiButton variant="ghost" :loading="status === 'loading'" @click="runNow">Re-run analysis</PiButton>
          <span v-if="lastRunLabel" class="t-mono t-tertiary" style="font-size: var(--text-xs);">Updated {{ lastRunLabel }}</span>
        </div>
        <PiButton variant="danger" icon="trash" @click="confirmDel = true">Delete all financial data</PiButton>
      </div>
    </template>
  </div>

  <ConfirmModal
    :open="confirmDel"
    danger
    confirmLabel="Delete all financial data"
    title="Delete all financial data?"
    body="This permanently removes every financial file and the insights drawn from them. Your brain keeps everything else. This cannot be undone."
    @close="confirmDel = false"
    @confirm="deleteAll"
  />
</template>
