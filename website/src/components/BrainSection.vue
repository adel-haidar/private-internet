<script setup lang="ts">
import BrainPulse from './BrainPulse.vue'
import BrainHealthPreview from './BrainHealthPreview.vue'
import Reveal from './Reveal.vue'

defineProps<{ t: Record<string, any> }>()
</script>

<template>
  <section class="mk-section" id="brain">
    <div class="mk-wrap">
      <div style="text-align:center;margin-bottom:var(--space-10)">
        <Reveal><div class="mk-label">{{ t.brain.label }}</div></Reveal>
        <Reveal :delay="60">
          <h2 class="mk-title" style="max-width:720px;margin:16px auto 0">
            <span style="display:block">{{ t.brain.t1 }}</span>
            <span style="display:block">{{ t.brain.t2 }}</span>
            <span style="display:block">{{ t.brain.t3 }}</span>
          </h2>
        </Reveal>
        <Reveal :delay="120">
          <div style="display:flex;justify-content:center;margin-top:var(--space-8)">
            <BrainPulse :size="48" :slow="true" />
          </div>
        </Reveal>
      </div>
      <div class="mk-brain__cols">
        <Reveal class-name="mk-brain__left">
          <p>{{ t.brain.p1 }}</p>
          <p>{{ t.brain.p2 }}</p>
          <p>{{ t.brain.p3 }}</p>
        </Reveal>
        <Reveal :delay="120" class-name="mk-brain__right">
          <BrainHealthPreview :t="t.brain" />
          <div class="mk-caption">{{ t.brain.caption }}</div>
        </Reveal>
      </div>
      <Reveal>
        <div class="mk-brain__stats">
          <div v-for="(s, i) in [t.brain.stat1, t.brain.stat2, t.brain.stat3]" :key="i" class="mk-stat">
            <div class="mk-stat__num">{{ s.split(' ')[0] }}</div>
            <div class="mk-stat__label">{{ s.split(' ').slice(1).join(' ') }}</div>
          </div>
        </div>
      </Reveal>
    </div>
  </section>
</template>
