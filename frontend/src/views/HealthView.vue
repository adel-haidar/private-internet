<script setup lang="ts">
import { ref, computed, watch, nextTick, onBeforeUnmount, onMounted } from 'vue'
import {
  Chart,
  LineElement, PointElement, LineController,
  BarElement, BarController,
  CategoryScale, LinearScale,
  Tooltip,
  type ChartConfiguration,
} from 'chart.js'
import PageHead from '../components/ui/PageHead.vue'
import PiCard from '../components/ui/PiCard.vue'
import PIIcon from '../components/ui/PIIcon.vue'
import PiButton from '../components/ui/PiButton.vue'
import UploadBanner from '../components/ui/UploadBanner.vue'
import StatusPill from '../components/ui/StatusPill.vue'
import InsightCard from '../components/ui/InsightCard.vue'
import InsightLine from '../components/ui/InsightLine.vue'
import DeviceCard from '../components/ui/DeviceCard.vue'
import ConfirmModal from '../components/ui/ConfirmModal.vue'
import HealthExportTeaser from '../components/health/HealthExportTeaser.vue'
import HealthExportGuide from '../components/health/HealthExportGuide.vue'
import { useHealthDaily, useHealthTrends, useAppleHealthImport } from '../composables/useHealth'
import { requireAuth } from '../composables/useAuth'
import { API_BASE } from '../config/env'
import { useToast } from '../components/ui/useToast'

Chart.register(
  LineElement, PointElement, LineController,
  BarElement, BarController,
  CategoryScale, LinearScale,
  Tooltip,
)

// ── Composables ─────────────────────────────────────────────────────────────
const { status: dailyStatus, result: daily, error: dailyError, fetchDaily } = useHealthDaily()
const { status: trendStatus, trends, error: trendError, fetchTrends } = useHealthTrends()
const { status: importStatus, error: importError, uploadFile } = useAppleHealthImport()
const toast = useToast()

const today = new Date().toISOString().slice(0, 10)
const trendDays = ref(30)

// Whether the user has any analysed data yet.
const populated = computed(() => !!(daily.value && daily.value.status !== 'not_run'))

// ── Export guide ──────────────────────────────────────────────────────────────
const guideOpen     = ref(false)
const guidePlatform = ref<'ios' | 'android'>('ios')
function openGuide(platform: 'ios' | 'android') {
  guidePlatform.value = platform
  guideOpen.value     = true
}

// ── Apple Health upload ────────────────────────────────────────────────────────
const ahInput = ref<HTMLInputElement | null>(null)
function pickFile() { ahInput.value?.click() }

async function onPickFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file  = input.files?.[0]
  input.value = ''
  if (file) await doUpload(file)
}

async function doUpload(file: File) {
  try {
    const r = await uploadFile(file)
    toast(`Imported ${r.inserted} health records (${r.date_range[0]} → ${r.date_range[1]})`, 'success')
    fetchDaily(today)
    fetchTrends(trendDays.value)
  } catch {
    toast(importError.value ?? 'Upload failed', 'error')
  }
}

// ── Devices ─────────────────────────────────────────────────────────────────
const appleConnected = computed(() =>
  (daily.value?.data_availability ?? []).some(a => a.source === 'apple_watch' && (a.available || a.last_data_date)),
)
const appleLastSync = computed(() =>
  (daily.value?.data_availability ?? []).find(a => a.source === 'apple_watch')?.last_data_date ?? undefined,
)

const devices = computed(() => [
  {
    icon: 'watch', name: 'Apple Watch', connected: appleConnected.value, lastSync: appleLastSync.value,
    acceptHint: 'Accepts .zip export from Health app',
    instructions: ['Open the Health app on iPhone', 'Tap your profile photo, then Export All Health Data', 'Upload the generated export.zip here'],
    appleHealth: true,
  },
  {
    icon: 'watch', name: 'Samsung Health', connected: false, acceptHint: 'Accepts .json / .zip',
    instructions: ['Open Samsung Health', 'Settings → Download personal data', 'Upload the archive here'],
    appleHealth: false,
  },
  {
    icon: 'device', name: 'Garmin', connected: false, acceptHint: 'Accepts .fit / .zip',
    instructions: ['Sign in to Garmin Connect on the web', 'Account → Export Your Data', 'Upload the archive here'],
    appleHealth: false,
  },
  {
    icon: 'scale', name: 'Smart Scale', connected: false, acceptHint: 'Accepts .csv',
    instructions: ['Open your scale’s companion app', 'Export weight history as CSV', 'Upload the file here'],
    appleHealth: false,
  },
])

async function onDeviceFiles(device: { appleHealth: boolean }, files: File[]) {
  const file = files[0]
  if (!file) return
  if (device.appleHealth) {
    await doUpload(file)
    return
  }
  // Other devices: index the raw export into the brain.
  try {
    const token = await requireAuth()
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${API_BASE}/api/file`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd })
    toast(res.ok ? 'File added to your brain' : 'Upload failed', res.ok ? 'success' : 'error')
  } catch {
    toast('Upload failed', 'error')
  }
}

// ── Formatting ────────────────────────────────────────────────────────────────
function fmtKg(v: number | null | undefined): string { return v != null ? `${v.toFixed(1)} kg` : '—' }
function fmtBpm(v: number | null | undefined): string { return v != null ? `${v.toFixed(0)} bpm` : '—' }
function fmtSteps(v: number | null | undefined): string { return v != null ? v.toLocaleString() : '—' }
function fmtSleep(v: number | null | undefined): string {
  if (v == null) return '—'
  const h = Math.floor(v / 60)
  const m = Math.round(v % 60)
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

const statRow = computed(() => {
  const s = daily.value?.summary
  return [
    { label: 'Steps today',         value: fmtSteps(s?.steps) },
    { label: 'Resting heart rate',  value: fmtBpm(s?.resting_hr) },
    { label: 'Sleep',               value: fmtSleep(s?.sleep_duration_min) },
    { label: 'Weight',              value: fmtKg(s?.weight_kg) },
  ]
})

// ── "Your body at a glance" ─────────────────────────────────────────────────
const trend = computed(() => daily.value?.summary.weight_trend_kg_per_week ?? null)
const flags = computed(() => daily.value?.flags ?? [])

const glanceStatus = computed<{ kind: 'good' | 'watch' | 'attention'; text: string }>(() => {
  if (flags.value.includes('goal_reached')) return { kind: 'good', text: 'Goal reached' }
  if (flags.value.includes('weight_loss_too_fast')) return { kind: 'attention', text: 'Losing too fast' }
  if (trend.value != null && trend.value < 0) return { kind: 'good', text: 'On track' }
  return { kind: 'watch', text: 'Steady' }
})

function fmtTrend(v: number | null): string {
  if (v == null) return '—'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(1)} kg/wk`
}
const trendIcon  = computed(() => (trend.value != null && trend.value < 0 ? 'down' : 'arrowRight'))
const trendColor = computed(() => {
  if (trend.value == null) return 'var(--text-secondary)'
  if (trend.value < 0) return 'var(--success)'
  if (trend.value > 0) return 'var(--warning)'
  return 'var(--text-secondary)'
})

// ── "What your numbers mean" — derived from flags ────────────────────────────
const showNumbers = ref(false)

interface Line { kind: 'good' | 'watch' | 'attention' | 'info'; label: string; text: string; raw?: string }
const numberLines = computed<Line[]>(() => {
  const s = daily.value?.summary
  const out: Line[] = []
  for (const f of flags.value) {
    switch (f) {
      case 'low_hrv_3_days':
        out.push({ kind: 'watch', label: 'Watch', text: 'Your heart-rate variability has been low for several days, which can signal fatigue or stress. Lighter training and earlier nights help.', raw: s?.hrv_ms != null ? `HRV ${s.hrv_ms} ms` : undefined })
        break
      case 'sleep_below_target':
        out.push({ kind: 'watch', label: 'Watch', text: "You've been sleeping below your target. Recovery happens during sleep — aim for an earlier, more consistent bedtime.", raw: s?.sleep_duration_min != null ? `Sleep ${fmtSleep(s.sleep_duration_min)}` : undefined })
        break
      case 'resting_hr_elevated':
        out.push({ kind: 'watch', label: 'Watch', text: 'Your resting heart rate is higher than usual, which often follows poor sleep or added stress.', raw: s?.resting_hr != null ? `Resting HR ${s.resting_hr.toFixed(0)} bpm` : undefined })
        break
      case 'weight_loss_too_fast':
        out.push({ kind: 'attention', label: 'Attention', text: "You're losing weight quite fast. Rapid loss is hard to sustain and can cost muscle — consider easing the deficit.", raw: `Trend ${fmtTrend(trend.value)}` })
        break
      case 'weight_plateau':
        out.push({ kind: 'info', label: 'Steady', text: "Your weight has been steady recently. If you're aiming to change it, small consistent adjustments work best.", raw: s?.weight_kg != null ? `Weight ${fmtKg(s.weight_kg)}` : undefined })
        break
      case 'goal_reached':
        out.push({ kind: 'good', label: 'Healthy', text: "You've reached your weight goal. The focus now shifts to maintaining it.", raw: s?.weight_kg != null ? `Weight ${fmtKg(s.weight_kg)}` : undefined })
        break
      default:
        out.push({ kind: 'info', label: 'Note', text: f.replace(/_/g, ' ') })
    }
  }
  if (out.length === 0) {
    out.push({ kind: 'good', label: 'Healthy', text: 'Your recent metrics are within a healthy range. Keep up your current habits.' })
  }
  return out
})

// ── "What your data suggests" ────────────────────────────────────────────────
const dataSuggests = computed(() =>
  daily.value?.analysis || daily.value?.coach_insight || daily.value?.reasoning || '',
)

// ── Detailed charts (collapsed) ──────────────────────────────────────────────
const chartsOpen = ref(false)

const chartWeightRef = ref<HTMLCanvasElement | null>(null)
const chartHrRef     = ref<HTMLCanvasElement | null>(null)
const chartHrvRef    = ref<HTMLCanvasElement | null>(null)
const chartSleepRef  = ref<HTMLCanvasElement | null>(null)
const chartStepsRef  = ref<HTMLCanvasElement | null>(null)

let chartWeight: Chart | null = null
let chartHr:     Chart | null = null
let chartHrv:    Chart | null = null
let chartSleep:  Chart | null = null
let chartSteps:  Chart | null = null

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}
function tooltipDefaults() {
  return {
    backgroundColor: cssVar('--background-raised'),
    titleColor:      cssVar('--text-primary'),
    bodyColor:       cssVar('--text-secondary'),
    borderColor:     cssVar('--border-subtle'),
    borderWidth:     1,
    titleFont:       { family: cssVar('--font-mono'), size: 11 },
    bodyFont:        { family: cssVar('--font-mono'), size: 11 },
  }
}
function makeScales(yLabel?: string) {
  const border = cssVar('--border-subtle')
  const text2  = cssVar('--text-secondary')
  return {
    x: {
      grid:  { color: `${border}60`, borderColor: 'transparent' },
      ticks: { color: text2, font: { family: cssVar('--font-mono'), size: 10 }, maxRotation: 0, maxTicksLimit: 8 },
    },
    y: {
      grid:  { color: `${border}60`, borderColor: 'transparent' },
      ticks: { color: text2, font: { family: cssVar('--font-mono'), size: 10 } },
      title: yLabel
        ? { display: true, text: yLabel, color: text2, font: { family: cssVar('--font-mono'), size: 9 } }
        : undefined,
    },
  }
}
const BASE_OPTS = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }

function destroyCharts() {
  chartWeight?.destroy(); chartWeight = null
  chartHr?.destroy();     chartHr     = null
  chartHrv?.destroy();    chartHrv    = null
  chartSleep?.destroy();  chartSleep  = null
  chartSteps?.destroy();  chartSteps  = null
}

function buildCharts() {
  destroyCharts()
  if (!trends.value) return

  const series  = trends.value.series
  const accent  = cssVar('--accent-primary') || '#5B5BD6'
  const amber   = cssVar('--brain-amber') || '#E8A444'
  const success = cssVar('--success') || '#2D7A4F'
  const danger  = cssVar('--danger') || '#C0392B'

  if (chartWeightRef.value) {
    const wData = series['weight_kg'] ?? []
    const labels = wData.map(p => p.date.slice(5))
    const weights = wData.map(p => p.value)
    const avg7: (number | null)[] = weights.map((_, i) => {
      if (i < 6) return null
      const slice = weights.slice(i - 6, i + 1)
      return slice.reduce((s, v) => s + v, 0) / slice.length
    })
    const goalLine = labels.map(() => 73)
    const cfg: ChartConfiguration<'line'> = {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Weight', data: weights, borderColor: accent, borderWidth: 1.5, pointRadius: 2, pointBackgroundColor: accent, fill: false, tension: 0.3, spanGaps: true },
          { label: '7-day avg', data: avg7, borderColor: amber, borderWidth: 2, pointRadius: 0, fill: false, tension: 0.4, spanGaps: true },
          { label: 'Goal 73kg', data: goalLine, borderColor: success, borderDash: [4, 4], borderWidth: 1.5, pointRadius: 0, fill: false },
        ],
      },
      options: {
        ...BASE_OPTS,
        scales: makeScales('kg'),
        plugins: { legend: { display: false }, tooltip: { ...tooltipDefaults(), callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${typeof ctx.parsed.y === 'number' ? ctx.parsed.y.toFixed(1) : '—'} kg` } } },
      },
    }
    chartWeight = new Chart(chartWeightRef.value, cfg)
  }

  if (chartHrRef.value) {
    const hrData = (series['resting_hr'] ?? []).slice(-14)
    const cfg: ChartConfiguration<'line'> = {
      type: 'line',
      data: { labels: hrData.map(p => p.date.slice(5)), datasets: [{ data: hrData.map(p => p.value), borderColor: amber, borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.35, spanGaps: true }] },
      options: { ...BASE_OPTS, scales: makeScales('bpm'), plugins: { legend: { display: false }, tooltip: { ...tooltipDefaults(), callbacks: { label: (ctx) => ` ${ctx.parsed.y} bpm` } } } },
    }
    chartHr = new Chart(chartHrRef.value, cfg)
  }

  if (chartHrvRef.value) {
    const hrvData = (series['hrv_ms'] ?? []).slice(-14)
    const cfg: ChartConfiguration<'line'> = {
      type: 'line',
      data: { labels: hrvData.map(p => p.date.slice(5)), datasets: [{ data: hrvData.map(p => p.value), borderColor: success, borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.35, spanGaps: true }] },
      options: { ...BASE_OPTS, scales: makeScales('ms'), plugins: { legend: { display: false }, tooltip: { ...tooltipDefaults(), callbacks: { label: (ctx) => ` ${ctx.parsed.y} ms` } } } },
    }
    chartHrv = new Chart(chartHrvRef.value, cfg)
  }

  if (chartSleepRef.value) {
    const sleepData = (series['sleep_duration_min'] ?? []).slice(-7)
    const values    = sleepData.map(p => +(p.value / 60).toFixed(2))
    const colors    = values.map(v => v >= 7 ? success : danger)
    const cfg: ChartConfiguration = {
      type: 'bar',
      data: {
        labels: sleepData.map(p => p.date.slice(5)),
        datasets: [
          { label: 'Sleep (h)', data: values, backgroundColor: colors, borderWidth: 0 } as any,
          { label: 'Target', data: values.map(() => 8), type: 'line', borderColor: amber, borderDash: [4, 4], borderWidth: 1.5, pointRadius: 0, fill: false } as any,
        ],
      },
      options: { ...BASE_OPTS, scales: { ...makeScales('h'), y: { ...makeScales('h').y, min: 0, max: 10 } }, plugins: { legend: { display: false }, tooltip: { ...tooltipDefaults(), callbacks: { label: (ctx: any) => ` ${ctx.parsed.y} h` } } } },
    }
    chartSleep = new Chart(chartSleepRef.value, cfg)
  }

  if (chartStepsRef.value) {
    const stepsData = (series['steps'] ?? []).slice(-7)
    const cfg: ChartConfiguration<'bar'> = {
      type: 'bar',
      data: { labels: stepsData.map(p => p.date.slice(5)), datasets: [{ label: 'Steps', data: stepsData.map(p => p.value), backgroundColor: accent, borderWidth: 0 }] },
      options: { ...BASE_OPTS, scales: makeScales('steps'), plugins: { legend: { display: false }, tooltip: { ...tooltipDefaults(), callbacks: { label: (ctx) => ` ${ctx.parsed.y?.toLocaleString() ?? 0} steps` } } } },
    }
    chartSteps = new Chart(chartStepsRef.value, cfg)
  }
}

function refreshChartsIfOpen() {
  if (chartsOpen.value) nextTick(() => buildCharts())
}
watch(chartsOpen, (open) => { if (open) nextTick(() => buildCharts()); else destroyCharts() })
watch(trends, refreshChartsIfOpen)
watch(trendDays, (d) => fetchTrends(d))
onBeforeUnmount(destroyCharts)

// ── Delete all health data ───────────────────────────────────────────────────
const confirmDel = ref(false)
async function deleteAll() {
  confirmDel.value = false
  // NOTE: backend DELETE endpoint for health data is not implemented yet.
  try {
    const token = await requireAuth()
    const res = await fetch(`${API_BASE}/api/health/data`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
    if (res.ok) {
      toast('Health data deleted', 'warning')
      fetchDaily(today)
      fetchTrends(trendDays.value)
    } else {
      toast('Deleting health data isn’t available yet.', 'error')
    }
  } catch {
    toast('Deleting health data isn’t available yet.', 'error')
  }
}

// ── Load ─────────────────────────────────────────────────────────────────────
onMounted(() => {
  fetchDaily(today)
  fetchTrends(trendDays.value)
})
</script>

<template>
  <div style="max-width: var(--content-dashboard); margin: 0 auto;">
    <PageHead
      title="Health"
      desc="Upload your health data and your brain turns it into a plain-language summary. Everything stays on your server."
    />

    <input ref="ahInput" type="file" accept=".zip,.xml" hidden @change="onPickFile" />

    <!-- Loading / error -->
    <PiCard v-if="dailyStatus === 'loading'" style="margin-bottom: var(--space-6);">
      <div class="pi-progress pi-progress--thin"><div class="pi-progress__track"><div class="pi-progress__fill" style="width: 40%;" /></div></div>
      <p class="t-secondary" style="font-size: var(--text-sm); margin-top: var(--space-3);">Running health workflow… fetching metrics, computing trends, generating insight.</p>
    </PiCard>
    <PiCard v-if="dailyStatus === 'error' && dailyError" style="border-color: var(--danger); margin-bottom: var(--space-6);">
      <span style="color: var(--danger); font-size: var(--text-sm);">{{ dailyError }}</span>
    </PiCard>

    <!-- Empty / first-run upload banner -->
    <div v-if="!populated && dailyStatus !== 'loading'" style="margin-bottom: var(--space-6);">
      <UploadBanner
        tone="amber"
        icon="health"
        title="Get your health analysis"
        intro="Upload any of the following and your brain will generate a plain-language summary of your health — no medical background needed to understand it."
        :items="[
          'Blood test results (PDF or image)',
          'Doctor reports or prescriptions',
          'Apple Health / Samsung Health exports (.zip or .xml)',
          'Wearable data from Garmin, Fitbit, or similar',
          'Scale exports or manual weight logs',
        ]"
        note="Your data stays on your server. You can delete everything from Brain → Manage data at any time."
      >
        <template #actions>
          <PiButton variant="cta" icon="upload" :loading="importStatus === 'uploading'" @click="pickFile">Upload health files</PiButton>
          <PiButton variant="secondary" @click="openGuide('ios')">Connect a device</PiButton>
        </template>
      </UploadBanner>
    </div>

    <!-- Devices -->
    <div style="display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-4);">
      <div style="font-family: var(--font-display); font-weight: 600; font-size: var(--text-md);">Devices</div>
      <PiButton variant="ghost" size="compact" @click="openGuide('ios')">How to export from Apple Health</PiButton>
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: var(--space-4); margin-bottom: var(--space-8);">
      <DeviceCard
        v-for="d in devices"
        :key="d.name"
        :icon="d.icon"
        :name="d.name"
        :connected="d.connected"
        :lastSync="d.lastSync"
        :instructions="d.instructions"
        :acceptHint="d.acceptHint"
        @files="onDeviceFiles(d, $event)"
      />
    </div>

    <!-- Populated -->
    <template v-if="populated">
      <!-- Metric stat row -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: var(--space-4); margin-bottom: var(--space-6);">
        <PiCard v-for="stat in statRow" :key="stat.label">
          <div style="font-family: var(--font-display); font-weight: 600; font-size: 24px; letter-spacing: -0.01em;">{{ stat.value }}</div>
          <div class="t-secondary" style="font-size: 12px;">{{ stat.label }}</div>
        </PiCard>
      </div>

      <!-- Plain-language insight cards -->
      <div class="pi-insight-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); margin-bottom: var(--space-4);">
        <InsightCard title="Your body at a glance">
          <template #status><StatusPill :kind="glanceStatus.kind">{{ glanceStatus.text }}</StatusPill></template>
          <p class="pi-insight__lead" style="margin-bottom: var(--space-4);">
            {{ daily?.coach_insight }}
          </p>
          <div style="display: flex; gap: var(--space-8); flex-wrap: wrap;">
            <div>
              <div class="t-secondary" style="font-size: var(--text-sm); margin-bottom: 4px;">Weight trend</div>
              <div :style="{ display: 'flex', alignItems: 'center', gap: '6px', color: trendColor, fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 'var(--text-md)' }">
                <PIIcon :name="trendIcon" :size="16" /><span class="t-mono">{{ fmtTrend(trend) }}</span>
              </div>
            </div>
            <div v-if="daily?.summary.progress_to_goal_kg != null">
              <div class="t-secondary" style="font-size: var(--text-sm); margin-bottom: 4px;">To goal (73 kg)</div>
              <StatusPill :kind="(daily?.summary.progress_to_goal_kg ?? 1) <= 0 ? 'good' : 'watch'">{{ fmtKg(daily?.summary.progress_to_goal_kg) }}</StatusPill>
            </div>
          </div>
        </InsightCard>

        <InsightCard title="What your numbers mean">
          <template #footer>
            <button class="pi-show-numbers" @click="showNumbers = !showNumbers">{{ showNumbers ? 'Hide numbers' : 'Show numbers' }}</button>
          </template>
          <InsightLine
            v-for="(line, i) in numberLines"
            :key="i"
            :kind="line.kind"
            :label="line.label"
            :text="line.text"
            :raw="line.raw"
            :showRaw="showNumbers"
          />
        </InsightCard>
      </div>

      <!-- What your data suggests -->
      <div v-if="dataSuggests" style="margin-bottom: var(--space-6);">
        <InsightCard title="What your data suggests">
          <p class="pi-insight__lead">{{ dataSuggests }}</p>
        </InsightCard>
      </div>

      <!-- Detailed charts — collapsed -->
      <PiCard style="margin-bottom: var(--space-6);">
        <div :class="['pi-collapse', chartsOpen ? 'pi-collapse--open' : '']">
          <button type="button" class="pi-collapse__toggle" :aria-expanded="chartsOpen" @click="chartsOpen = !chartsOpen">
            <PIIcon name="chevronRight" :size="14" />Show detailed charts
          </button>
          <div v-if="chartsOpen" class="pi-collapse__body">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-4);">
              <div style="font-family: var(--font-display); font-weight: 500;">Trends</div>
              <div class="pi-pills">
                <button v-for="d in [30, 90]" :key="d" :class="['pi-pill', trendDays === d ? 'pi-pill--active' : '']" @click="trendDays = d">{{ d }}D</button>
              </div>
            </div>
            <div v-if="trendStatus === 'error'" style="color: var(--danger); font-size: var(--text-sm); margin-bottom: var(--space-4);">{{ trendError }}</div>

            <div style="font-family: var(--font-display); font-weight: 500; font-size: var(--text-sm); margin-bottom: var(--space-2);">Weight · last {{ trendDays }} days</div>
            <div style="height: 240px; position: relative; margin-bottom: var(--space-6);"><canvas ref="chartWeightRef" /></div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-5); margin-bottom: var(--space-6);">
              <div>
                <div style="font-family: var(--font-display); font-weight: 500; font-size: var(--text-sm); margin-bottom: var(--space-2);">Resting heart rate · last 14 days</div>
                <div style="height: 160px; position: relative;"><canvas ref="chartHrRef" /></div>
              </div>
              <div>
                <div style="font-family: var(--font-display); font-weight: 500; font-size: var(--text-sm); margin-bottom: var(--space-2);">HRV · last 14 days</div>
                <div style="height: 160px; position: relative;"><canvas ref="chartHrvRef" /></div>
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-5);">
              <div>
                <div style="font-family: var(--font-display); font-weight: 500; font-size: var(--text-sm); margin-bottom: var(--space-2);">Sleep · last 7 days</div>
                <div style="height: 160px; position: relative;"><canvas ref="chartSleepRef" /></div>
              </div>
              <div>
                <div style="font-family: var(--font-display); font-weight: 500; font-size: var(--text-sm); margin-bottom: var(--space-2);">Steps · last 7 days</div>
                <div style="height: 160px; position: relative;"><canvas ref="chartStepsRef" /></div>
              </div>
            </div>
          </div>
        </div>
      </PiCard>

      <!-- Actions -->
      <div style="display: flex; justify-content: space-between; gap: var(--space-3); flex-wrap: wrap;">
        <PiButton variant="ghost" icon="plus" :loading="importStatus === 'uploading'" @click="pickFile">Upload more data</PiButton>
        <PiButton variant="danger" icon="trash" @click="confirmDel = true">Delete all health data</PiButton>
      </div>
    </template>

    <!-- Export guide teaser (shown in empty state to guide first upload) -->
    <div v-if="!populated && dailyStatus !== 'loading'" style="margin-top: var(--space-8);">
      <HealthExportTeaser @open="openGuide" />
    </div>
  </div>

  <!-- Export guide modal -->
  <HealthExportGuide
    :open="guideOpen"
    :platform="guidePlatform"
    @close="guideOpen = false"
    @update:platform="guidePlatform = $event"
  />

  <!-- Delete confirmation -->
  <ConfirmModal
    :open="confirmDel"
    danger
    confirmLabel="Delete all health data"
    title="Delete all health data?"
    body="This permanently removes every health file and the insights drawn from them. Your brain keeps everything else. This cannot be undone."
    @close="confirmDel = false"
    @confirm="deleteAll"
  />
</template>
