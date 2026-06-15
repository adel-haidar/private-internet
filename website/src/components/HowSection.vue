<script setup lang="ts">
import SectionHead from './SectionHead.vue'
import Reveal from './Reveal.vue'

defineProps<{ t: Record<string, any> }>()
</script>

<template>
  <section class="mk-section" id="how">
    <div class="mk-wrap">
      <SectionHead :label="t.how.label" :title="t.how.title" />
      <div class="mk-steps">
        <Reveal v-for="(s, i) in [
          { n:'01', title:t.how.s1t, body:t.how.s1b },
          { n:'02', title:t.how.s2t, body:t.how.s2b },
          { n:'03', title:t.how.s3t, body:t.how.s3b },
        ]" :key="s.n" :delay="i * 100">
          <div class="mk-step">
            <div class="mk-step__num">{{ s.n }}</div>
            <div class="mk-step__title">{{ s.title }}</div>
            <div class="mk-step__body">{{ s.body }}</div>
          </div>
        </Reveal>
      </div>
    </div>
  </section>
</template>
