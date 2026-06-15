<script setup lang="ts">
import SectionHead from './SectionHead.vue'
import Reveal from './Reveal.vue'

defineProps<{ t: Record<string, any> }>()
</script>

<template>
  <section class="mk-section" id="problem" style="background:var(--background-surface);border-top:1px solid var(--border-subtle)">
    <div class="mk-wrap">
      <SectionHead :label="t.problem.label" :title="t.problem.title" :body="t.problem.body" :max-title="680" :max-body="600" />
      <Reveal>
        <div class="mk-problem__cards">
          <div v-for="(c, i) in [t.problem.c1, t.problem.c2, t.problem.c3]" :key="i" class="mk-stmt-card">{{ c }}</div>
        </div>
      </Reveal>
      <Reveal :delay="120">
        <p class="t-serif" style="text-align:center;font-style:italic;color:var(--text-tertiary);font-size:18px;margin-top:var(--space-10)">{{ t.problem.transition }}</p>
      </Reveal>
    </div>
  </section>
</template>
