<script setup lang="ts">
import SectionHead from './SectionHead.vue'
import Reveal from './Reveal.vue'
import PiButton from './PiButton.vue'
import PiTag from './PiTag.vue'

defineProps<{ t: Record<string, any> }>()

const rowKeys = ['cpu', 'ram', 'storage', 'gpu', 'os', 'net']
const llms = ['ollama', 'lm', 'llama']
const vdbs = ['pg', 'qdrant', 'chroma']

function openInstallGuide() {
  window.open('https://github.com/private-internet/private-internet#self-hosting', '_blank')
}
</script>

<template>
  <section class="mk-section" id="hardware" style="background:var(--background-surface)">
    <div class="mk-wrap">
      <SectionHead :label="t.hardware.label" :title="t.hardware.title" :body="t.hardware.body" :max-body="620" />

      <div class="mk-hw__tiers">
        <Reveal>
          <div class="mk-hw-card mk-hw-card--min">
            <div class="mk-hw-card__head">
              <span class="mk-hw-card__title">{{ t.hardware.minTitle }}</span>
              <span class="mk-hw-card__sub">{{ t.hardware.minSub }}</span>
            </div>
            <div v-for="k in rowKeys" :key="k" class="mk-hw-row">
              <span class="mk-hw-row__label">{{ t.hardware.rows[k] }}</span>
              <span class="mk-hw-row__val">{{ t.hardware.min[k] }}</span>
            </div>
          </div>
        </Reveal>
        <Reveal :delay="100">
          <div class="mk-hw-card mk-hw-card--rec">
            <div class="mk-hw-card__head">
              <span class="mk-hw-card__title">{{ t.hardware.recTitle }}</span>
              <span class="mk-hw-card__sub">{{ t.hardware.recSub }}</span>
            </div>
            <div v-for="k in rowKeys" :key="k" class="mk-hw-row">
              <span class="mk-hw-row__label">{{ t.hardware.rows[k] }}</span>
              <span class="mk-hw-row__val">{{ t.hardware.rec[k] }}</span>
            </div>
          </div>
        </Reveal>
      </div>

      <Reveal>
        <h3 class="mk-subhead" style="margin-top:var(--space-12)">
          {{ t.hardware.llmTitle }}<span class="mk-subhead__note">{{ t.hardware.llmSub }}</span>
        </h3>
      </Reveal>
      <Reveal>
        <div class="mk-hw-opts">
          <div v-for="k in llms" :key="k" class="mk-opt-card">
            <div class="mk-opt-card__name">
              {{ t.hardware.llm[k].name }}
              <PiTag v-if="t.hardware.llm[k].tag">{{ t.hardware.llm[k].tag }}</PiTag>
            </div>
            <p class="mk-opt-card__desc">{{ t.hardware.llm[k].desc }}</p>
            <code v-if="k === 'ollama'" class="mk-code">ollama pull llama3.1:8b</code>
          </div>
        </div>
      </Reveal>

      <Reveal>
        <h3 class="mk-subhead" style="margin-top:var(--space-10)">{{ t.hardware.vdbTitle }}</h3>
      </Reveal>
      <Reveal>
        <div class="mk-hw-opts">
          <div v-for="k in vdbs" :key="k" class="mk-opt-card">
            <div class="mk-opt-card__name">
              {{ t.hardware.vdb[k].name }}
              <PiTag v-if="t.hardware.vdb[k].tag">{{ t.hardware.vdb[k].tag }}</PiTag>
            </div>
            <p class="mk-opt-card__desc">{{ t.hardware.vdb[k].desc }}</p>
          </div>
        </div>
      </Reveal>

      <Reveal>
        <div class="mk-hw-note">
          <p class="mk-hw-note__text">{{ t.hardware.note }}</p>
          <code class="mk-code" style="margin-top:var(--space-4);white-space:pre">{{ 'LOCAL_LLM_ENDPOINT=http://localhost:11434\nVECTOR_DB_TYPE=pgvector | qdrant | chroma' }}</code>
        </div>
      </Reveal>
      <Reveal>
        <div style="margin-top:var(--space-6)">
          <PiButton variant="secondary" icon="external" @click="openInstallGuide">{{ t.hardware.cta }}</PiButton>
        </div>
      </Reveal>
    </div>
  </section>
</template>
