<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount, onMounted } from 'vue'
import {
  Chart,
  LineElement, PointElement, LineController,
  BarElement, BarController,
  CategoryScale, LinearScale,
  Tooltip,
  type ChartConfiguration,
} from 'chart.js'
import { useHealthDaily, useHealthTrends } from '../composables/useHealth'

Chart.register(
  LineElement, PointElement, LineController,
  BarElement, BarController,
  CategoryScale, LinearScale,
  Tooltip,
)

// ── Composables ─────────────────────────────────────────────────────────────

const { status: dailyStatus, result: daily, error: dailyError, fetchDaily, runDaily } = useHealthDaily()
const { status: trendStatus, trends, error: trendError, fetchTrends } = useHealthTrends()

// ── Date + range controls ────────────────────────────────────────────────────

const today = new Date().toISOString().slice(0, 10)
const trendDays = ref(30)

// ── Chart refs ───────────────────────────────────────────────────────────────

const chartWeightRef  = ref<HTMLCanvasElement | null>(null)
const chartHrRef      = ref<HTMLCanvasElement | null>(null)
const chartHrvRef     = ref<HTMLCanvasElement | null>(null)
const chartSleepRef   = ref<HTMLCanvasElement | null>(null)
const chartStepsRef   = ref<HTMLCanvasElement | null>(null)

let chartWeight: Chart | null = null
let chartHr:     Chart | null = null
let chartHrv:    Chart | null = null
let chartSleep:  Chart | null = null
let chartSteps:  Chart | null = null

// ── Theme helpers ─────────────────────────────────────────────────────────────

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function tooltipDefaults() {
  return {
    backgroundColor: cssVar('--elevated'),
    titleColor:      cssVar('--text-1'),
    bodyColor:       cssVar('--text-2'),
    borderColor:     cssVar('--border'),
    borderWidth:     1,
    titleFont:       { family: cssVar('--font-mono'), size: 11 },
    bodyFont:        { family: cssVar('--font-mono'), size: 11 },
  }
}

function makeScales(yLabel?: string) {
  const border = cssVar('--border')
  const text2  = cssVar('--text-2')
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

const BASE_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
}

// ── Chart build/destroy ──────────────────────────────────────────────────────

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

  const series = trends.value.series
  const accent  = '#4A7FA5'
  const gold    = '#C4A455'
  const success = '#3A7A5A'

  // ── Weight chart ───────────────────────────────────────────────────────────

  if (chartWeightRef.value) {
    const wData = series['weight_kg'] ?? []
    const labels = wData.map(p => p.date.slice(5))  // MM-DD
    const weights = wData.map(p => p.value)

    // Compute 7-day rolling average
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
          {
            label: 'Weight',
            data: weights,
            borderColor: accent,
            borderWidth: 1.5,
            pointRadius: 2,
            pointBackgroundColor: accent,
            fill: false,
            tension: 0.3,
            spanGaps: true,
          },
          {
            label: '7-day avg',
            data: avg7,
            borderColor: gold,
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            tension: 0.4,
            spanGaps: true,
          },
          {
            label: 'Goal 73kg',
            data: goalLine,
            borderColor: success,
            borderDash: [4, 4],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
          },
        ],
      },
      options: {
        ...BASE_OPTS,
        scales: makeScales('kg'),
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipDefaults(),
            callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${typeof ctx.parsed.y === 'number' ? ctx.parsed.y.toFixed(1) : '—'} kg` },
          },
        },
      },
    }
    chartWeight = new Chart(chartWeightRef.value, cfg)
  }

  // ── Resting HR chart ──────────────────────────────────────────────────────

  if (chartHrRef.value) {
    const hrData = (series['resting_hr'] ?? []).slice(-14)
    const labels  = hrData.map(p => p.date.slice(5))
    const values  = hrData.map(p => p.value)
    const cfg: ChartConfiguration<'line'> = {
      type: 'line',
      data: {
        labels,
        datasets: [{
          data: values,
          borderColor: '#C4A455',
          borderWidth: 2,
          pointRadius: 2,
          pointBackgroundColor: '#C4A455',
          fill: { target: 'origin', above: 'rgba(196,164,85,0.07)' },
          tension: 0.35,
          spanGaps: true,
        }],
      },
      options: {
        ...BASE_OPTS,
        scales: makeScales('bpm'),
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipDefaults(),
            callbacks: { label: (ctx) => ` ${ctx.parsed.y} bpm` },
          },
        },
      },
    }
    chartHr = new Chart(chartHrRef.value, cfg)
  }

  // ── HRV chart ─────────────────────────────────────────────────────────────

  if (chartHrvRef.value) {
    const hrvData = (series['hrv_ms'] ?? []).slice(-14)
    const labels  = hrvData.map(p => p.date.slice(5))
    const values  = hrvData.map(p => p.value)
    const cfg: ChartConfiguration<'line'> = {
      type: 'line',
      data: {
        labels,
        datasets: [{
          data: values,
          borderColor: '#3A7A5A',
          borderWidth: 2,
          pointRadius: 2,
          pointBackgroundColor: '#3A7A5A',
          fill: { target: 'origin', above: 'rgba(58,122,90,0.08)' },
          tension: 0.35,
          spanGaps: true,
        }],
      },
      options: {
        ...BASE_OPTS,
        scales: makeScales('ms'),
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipDefaults(),
            callbacks: { label: (ctx) => ` ${ctx.parsed.y} ms` },
          },
        },
      },
    }
    chartHrv = new Chart(chartHrvRef.value, cfg)
  }

  // ── Sleep chart (bar vs 8h target) ────────────────────────────────────────

  if (chartSleepRef.value) {
    const sleepData = (series['sleep_duration_min'] ?? []).slice(-7)
    const labels    = sleepData.map(p => p.date.slice(5))
    const values    = sleepData.map(p => +(p.value / 60).toFixed(2))
    const colors    = values.map(v => v >= 7 ? 'rgba(58,122,90,0.75)' : 'rgba(122,58,58,0.75)')
    const target    = labels.map(() => 8)

    const cfg: ChartConfiguration = {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Sleep (h)',
            data: values,
            backgroundColor: colors,
            borderWidth: 0,
          } as any,
          {
            label: 'Target',
            data: target,
            type: 'line',
            borderColor: gold,
            borderDash: [4, 4],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
          } as any,
        ],
      },
      options: {
        ...BASE_OPTS,
        scales: { ...makeScales('h'), y: { ...makeScales('h').y, min: 0, max: 10 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipDefaults(),
            callbacks: { label: (ctx: any) => ` ${ctx.parsed.y} h` },
          },
        },
      },
    }
    chartSleep = new Chart(chartSleepRef.value, cfg)
  }

  // ── Steps chart ───────────────────────────────────────────────────────────

  if (chartStepsRef.value) {
    const stepsData = (series['steps'] ?? []).slice(-7)
    const labels    = stepsData.map(p => p.date.slice(5))
    const values    = stepsData.map(p => p.value)
    const cfg: ChartConfiguration<'bar'> = {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Steps',
          data: values,
          backgroundColor: 'rgba(74,127,165,0.65)',
          borderWidth: 0,
        }],
      },
      options: {
        ...BASE_OPTS,
        scales: makeScales('steps'),
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipDefaults(),
            callbacks: { label: (ctx) => ` ${ctx.parsed.y?.toLocaleString() ?? 0} steps` },
          },
        },
      },
    }
    chartSteps = new Chart(chartStepsRef.value, cfg)
  }
}

watch(trends, () => nextTick(() => buildCharts()))

onBeforeUnmount(destroyCharts)

// ── Flag display ─────────────────────────────────────────────────────────────

const FLAG_LABELS: Record<string, { label: string; cls: string }> = {
  low_hrv_3_days:        { label: 'LOW HRV — 3 DAYS',       cls: 'flag--warning' },
  sleep_below_target:    { label: 'SLEEP DEFICIT',           cls: 'flag--warning' },
  weight_plateau:        { label: 'WEIGHT PLATEAU',          cls: 'flag--info' },
  weight_loss_too_fast:  { label: 'LOSS TOO FAST',           cls: 'flag--danger' },
  resting_hr_elevated:   { label: 'HR ELEVATED',             cls: 'flag--warning' },
  goal_reached:          { label: 'GOAL REACHED',            cls: 'flag--success' },
}

function flagMeta(f: string) {
  return FLAG_LABELS[f] ?? { label: f.toUpperCase().replace(/_/g, ' '), cls: 'flag--info' }
}

// ── Data availability display ────────────────────────────────────────────────

const SOURCE_LABELS: Record<string, string> = {
  beurer_scale: 'SCALE',
  apple_watch:  'APPLE WATCH',
}

function sourceLabel(s: string): string {
  return SOURCE_LABELS[s] ?? s.toUpperCase().replace(/_/g, ' ')
}

// ── Formatting ────────────────────────────────────────────────────────────────

function fmtKg(v: number | null): string {
  return v !== null ? `${v.toFixed(1)} kg` : '—'
}
function fmtBpm(v: number | null): string {
  return v !== null ? `${v.toFixed(0)} bpm` : '—'
}
function fmtHours(v: number | null): string {
  if (v === null) return '—'
  const h = Math.floor(v / 60)
  const m = Math.round(v % 60)
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}
function fmtSteps(v: number | null): string {
  return v !== null ? v.toLocaleString() : '—'
}
function fmtTrend(v: number | null): string {
  if (v === null) return '—'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)} kg/wk`
}
function trendClass(v: number | null): string {
  if (v === null) return 'kpi-value--neutral'
  if (v < -1.2) return 'kpi-value--negative'
  if (v < 0)    return 'kpi-value--positive'
  return 'kpi-value--negative'
}

// ── Load on mount ─────────────────────────────────────────────────────────────

onMounted(() => {
  fetchDaily(today)
  fetchTrends(trendDays.value)
})

watch(trendDays, (d) => fetchTrends(d))
</script>

<template>
  <div class="page">

    <!-- ── Header ──────────────────────────────────────────────────────── -->
    <header class="page-header">
      <div class="header-left">
        <span class="page-tag">SECTION</span>
        <h1 class="page-title">HEALTH INTEL</h1>
      </div>
      <div class="header-actions">
        <span class="header-date">{{ today }}</span>
        <button
          class="btn btn--ghost"
          :disabled="dailyStatus === 'loading'"
          @click="fetchDaily(today)"
        >FETCH</button>
        <button
          class="btn btn--primary"
          :disabled="dailyStatus === 'loading'"
          @click="runDaily(today)"
        >RUN TODAY</button>
      </div>
    </header>
    <div class="rule" />

    <div class="body">

      <!-- ── Loading / error ─────────────────────────────────────────── -->
      <div v-if="dailyStatus === 'loading'" class="state-card state-card--loading">
        <div class="progress-track"><div class="progress-fill" /></div>
        <p class="state-hint">Running health workflow… fetching metrics, computing trends, generating insight.</p>
      </div>

      <div v-if="dailyStatus === 'error' && dailyError" class="state-card state-card--error">
        {{ dailyError }}
      </div>

      <!-- ── 0. No run stored for this date ───────────────────────────── -->
      <div v-if="daily && daily.status === 'not_run'" class="state-card state-card--notice">
        <div class="insight-label">// NO ANALYSIS STORED — {{ daily.date }}</div>
        <p class="notice-text">{{ daily.reasoning }}</p>
        <p class="state-hint">Press RUN TODAY to generate one.</p>
      </div>

      <!-- ── 1. Coach insight card ────────────────────────────────────── -->
      <template v-if="daily && daily.status !== 'not_run'">
        <div class="insight-card">
          <div class="insight-label">// DAILY COACHING NOTE — {{ daily.date }}</div>
          <p class="insight-text">{{ daily.coach_insight }}</p>
        </div>

        <!-- ── 1b. Device data availability ──────────────────────────── -->
        <div
          v-if="(daily.data_availability ?? []).some(a => !a.available)"
          class="availability-row"
        >
          <div
            v-for="a in (daily.data_availability ?? []).filter(a => !a.available)"
            :key="a.source"
            class="availability-card"
          >
            <span class="availability-source">{{ sourceLabel(a.source) }}</span>
            <span class="availability-text">
              no data for {{ daily.date }}
              <template v-if="a.last_data_date"> · last: {{ a.last_data_date }}</template>
              <template v-if="a.next_expected_date"> · expected: <strong>{{ a.next_expected_date }}</strong></template>
              <template v-if="!a.last_data_date"> · no data ingested yet</template>
            </span>
          </div>
        </div>

        <!-- ── 2. Active flags ───────────────────────────────────────── -->
        <div v-if="daily.flags.length > 0" class="flags-row">
          <span
            v-for="f in daily.flags"
            :key="f"
            class="flag-badge"
            :class="flagMeta(f).cls"
          >{{ flagMeta(f).label }}</span>
        </div>

        <!-- ── 3. KPI row ────────────────────────────────────────────── -->
        <div class="kpi-row">
          <div class="kpi-card">
            <div class="kpi-label">CURRENT WEIGHT</div>
            <div class="kpi-value kpi-value--neutral">{{ fmtKg(daily.summary.weight_kg) }}</div>
            <div class="kpi-sublabel">7-day avg: {{ fmtKg(daily.summary.weight_7day_avg) }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">TO GOAL (73 KG)</div>
            <div
              class="kpi-value"
              :class="(daily.summary.progress_to_goal_kg ?? 1) <= 0 ? 'kpi-value--positive' : 'kpi-value--neutral'"
            >{{ fmtKg(daily.summary.progress_to_goal_kg) }}</div>
            <div v-if="daily.summary.weeks_to_goal_at_current_rate" class="kpi-sublabel">
              ~{{ daily.summary.weeks_to_goal_at_current_rate }} weeks at current rate
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">WEEKLY TREND</div>
            <div class="kpi-value" :class="trendClass(daily.summary.weight_trend_kg_per_week)">
              {{ fmtTrend(daily.summary.weight_trend_kg_per_week) }}
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">RESTING HR</div>
            <div class="kpi-value kpi-value--neutral">{{ fmtBpm(daily.summary.resting_hr) }}</div>
            <div class="kpi-sublabel">7-day avg: {{ fmtBpm(daily.summary.resting_hr_7day_avg) }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">HRV</div>
            <div class="kpi-value kpi-value--neutral">
              {{ daily.summary.hrv_ms !== null ? `${daily.summary.hrv_ms} ms` : '—' }}
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">SLEEP LAST NIGHT</div>
            <div
              class="kpi-value"
              :class="(daily.summary.sleep_duration_min ?? 999) >= 420 ? 'kpi-value--positive' : 'kpi-value--negative'"
            >{{ fmtHours(daily.summary.sleep_duration_min) }}</div>
            <div class="kpi-sublabel">Steps: {{ fmtSteps(daily.summary.steps) }}</div>
          </div>
        </div>

        <!-- ── 4. Analysis (from medical records + metrics) ──────────── -->
        <div v-if="daily.analysis" class="analysis-card">
          <div class="insight-label">// ANALYSIS — BASED ON MEDICAL RECORDS + DEVICE DATA</div>
          <p class="insight-text">{{ daily.analysis }}</p>
        </div>

        <!-- ── 5. Reasoning ──────────────────────────────────────────── -->
        <div v-if="daily.reasoning" class="reasoning-block">
          <div class="insight-label">// REASONING — WHY THIS ANALYSIS</div>
          <p class="reasoning-text">{{ daily.reasoning }}</p>
        </div>

        <!-- ── 6. Documents consulted ────────────────────────────────── -->
        <div v-if="(daily.documents ?? []).length > 0" class="documents-block">
          <div class="insight-label">// DOCUMENTS FETCHED FROM MEMORY ({{ (daily.documents ?? []).length }})</div>
          <ul class="documents-list">
            <li v-for="d in daily.documents" :key="d" class="document-item">{{ d }}</li>
          </ul>
        </div>
        <div v-else class="documents-block">
          <div class="insight-label">// DOCUMENTS FETCHED FROM MEMORY (0)</div>
          <p class="reasoning-text">No medical records found in the memory server.</p>
        </div>
      </template>

      <!-- ── Chart range selector ──────────────────────────────────────── -->
      <div class="section-block">
        <div class="section-label">
          TREND CHARTS
          <span class="range-pills">
            <button
              v-for="d in [30, 90]"
              :key="d"
              class="pill"
              :class="{ 'pill--active': trendDays === d }"
              @click="trendDays = d"
            >{{ d }}D</button>
          </span>
        </div>

        <div v-if="trendStatus === 'error'" class="state-card state-card--error">{{ trendError }}</div>

        <!-- ── 3. Weight chart ──────────────────────────────────────── -->
        <div class="chart-block">
          <div class="chart-title">WEIGHT — LAST {{ trendDays }} DAYS
            <span class="chart-legend">
              <span class="legend-dot" style="background:#4A7FA5"></span> daily
              <span class="legend-dot" style="background:#C4A455"></span> 7-day avg
              <span class="legend-dot" style="background:#3A7A5A"></span> goal 73 kg
            </span>
          </div>
          <div class="chart-wrap chart-wrap--tall">
            <canvas ref="chartWeightRef"></canvas>
          </div>
        </div>

        <!-- ── 4. Recovery metrics ─────────────────────────────────── -->
        <div class="chart-grid">
          <div class="chart-block">
            <div class="chart-title">RESTING HR — LAST 14 DAYS</div>
            <div class="chart-wrap">
              <canvas ref="chartHrRef"></canvas>
            </div>
          </div>
          <div class="chart-block">
            <div class="chart-title">HRV — LAST 14 DAYS</div>
            <div class="chart-wrap">
              <canvas ref="chartHrvRef"></canvas>
            </div>
          </div>
        </div>

        <!-- ── 5. Sleep & activity ─────────────────────────────────── -->
        <div class="chart-grid">
          <div class="chart-block">
            <div class="chart-title">SLEEP — LAST 7 DAYS
              <span class="chart-legend">
                <span class="legend-dot" style="background:#C4A455"></span> 8h target
              </span>
            </div>
            <div class="chart-wrap">
              <canvas ref="chartSleepRef"></canvas>
            </div>
          </div>
          <div class="chart-block">
            <div class="chart-title">STEPS — LAST 7 DAYS</div>
            <div class="chart-wrap">
              <canvas ref="chartStepsRef"></canvas>
            </div>
          </div>
        </div>

      </div>

    </div>
  </div>
</template>

<style scoped>
/* ── Shell ──────────────────────────────────────────────────────────────── */
.page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

/* ── Header ─────────────────────────────────────────────────────────────── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28px 32px 24px;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 16px;
}

.page-tag {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.14em;
  color: var(--text-muted);
  border: 1px solid var(--border);
  padding: 2px 6px;
}

.page-title {
  font-family: var(--font-mono);
  font-size: 18px;
  letter-spacing: 0.07em;
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-date {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 0.08em;
}

.rule {
  height: 1px;
  background: var(--border);
}

/* ── Body ───────────────────────────────────────────────────────────────── */
.body {
  padding: 28px 32px 48px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.btn {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  border: 1px solid var(--border);
  padding: 6px 14px;
  cursor: pointer;
  background: transparent;
  color: var(--text-2);
  transition: border-color 0.12s, color 0.12s, background 0.12s;
}
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn--ghost:hover:not(:disabled) { border-color: var(--accent); color: var(--text-1); }
.btn--primary {
  border-color: var(--accent);
  color: var(--accent);
}
.btn--primary:hover:not(:disabled) {
  background: var(--accent);
  color: var(--bg-base);
}

/* ── State cards ─────────────────────────────────────────────────────────── */
.state-card {
  border: 1px solid var(--border);
  padding: 16px 20px;
  background: var(--surface);
}
.state-card--loading { display: flex; flex-direction: column; gap: 10px; }
.state-card--error   { border-color: var(--status-error); color: var(--status-error); font-family: var(--font-mono); font-size: 11px; }

.progress-track {
  height: 2px;
  background: var(--border);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  width: 40%;
  background: var(--accent);
  animation: progressSweep 1.8s ease-in-out infinite;
}
@keyframes progressSweep {
  0%   { transform: translateX(-100%) scaleX(0.6); }
  50%  { transform: translateX(100px)  scaleX(1.2); }
  100% { transform: translateX(360%)   scaleX(0.6); }
}
.state-hint {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 0.08em;
}

/* ── Insight card ────────────────────────────────────────────────────────── */
.insight-card {
  border: 1px solid var(--accent);
  background: var(--surface);
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.insight-label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.14em;
  color: var(--text-muted);
}

.insight-text {
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-1);
}

.state-card--notice {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notice-text {
  font-family: var(--font-sans);
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-2);
}

/* ── Data availability ───────────────────────────────────────────────────── */
.availability-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.availability-card {
  border: 1px solid var(--status-processing);
  background: var(--surface);
  padding: 10px 14px;
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.availability-source {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.12em;
  color: var(--status-processing);
  border: 1px solid var(--status-processing);
  padding: 2px 6px;
  flex: 0 0 auto;
}

.availability-text {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-2);
  letter-spacing: 0.03em;
}

.availability-text strong { color: var(--text-1); font-weight: 500; }

/* ── Analysis / reasoning / documents ────────────────────────────────────── */
.analysis-card {
  border: 1px solid var(--border);
  background: var(--surface);
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reasoning-block,
.documents-block {
  border: 1px solid var(--border);
  border-left: 2px solid var(--accent);
  background: var(--surface);
  padding: 14px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reasoning-text {
  font-family: var(--font-sans);
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-2);
}

.documents-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.document-item {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-2);
  letter-spacing: 0.03em;
}

.document-item::before {
  content: '▸ ';
  color: var(--accent);
}

/* ── Flags ───────────────────────────────────────────────────────────────── */
.flags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.flag-badge {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.12em;
  padding: 3px 8px;
  border: 1px solid;
}

.flag--success { color: var(--status-active);     border-color: var(--status-active);     }
.flag--warning { color: var(--status-processing); border-color: var(--status-processing); }
.flag--danger  { color: var(--status-error);      border-color: var(--status-error);      }
.flag--info    { color: var(--text-2);            border-color: var(--border);            }

/* ── KPI row ─────────────────────────────────────────────────────────────── */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

@media (max-width: 1100px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 700px)  { .kpi-row { grid-template-columns: 1fr; } }

.kpi-card {
  border: 1px solid var(--border);
  background: var(--surface);
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.kpi-label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.12em;
  color: var(--text-muted);
}

.kpi-value {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 500;
  letter-spacing: -0.01em;
  line-height: 1;
}

.kpi-value--positive { color: var(--status-active); }
.kpi-value--negative { color: var(--status-error);  }
.kpi-value--neutral  { color: var(--text-primary);  }

.kpi-sublabel {
  font-family: var(--font-sans);
  font-size: 10px;
  color: var(--text-muted);
}

/* ── Section block ───────────────────────────────────────────────────────── */
.section-block {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--text-secondary);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* ── Range pills ─────────────────────────────────────────────────────────── */
.range-pills {
  display: flex;
  gap: 4px;
}

.pill {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.1em;
  border: 1px solid var(--border);
  padding: 2px 8px;
  cursor: pointer;
  background: transparent;
  color: var(--text-2);
  transition: border-color 0.1s, color 0.1s;
}
.pill:hover    { border-color: var(--accent); color: var(--text-1); }
.pill--active  { border-color: var(--accent); color: var(--accent); }

/* ── Charts ──────────────────────────────────────────────────────────────── */
.chart-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chart-title {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 12px;
}

.chart-legend {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-3);
}

.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
}

.chart-wrap {
  height: 180px;
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 8px;
}

.chart-wrap--tall { height: 240px; }

.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 900px) { .chart-grid { grid-template-columns: 1fr; } }
</style>
