<script setup lang="ts">
import Reveal from './Reveal.vue'
import SectionHead from './SectionHead.vue'
import ModulePreviews from './ModulePreviews.vue'

defineProps<{ t: Record<string, any> }>()

const order = ['pulse', 'signal', 'stories', 'aria', 'health', 'finances']
</script>

<template>
  <section id="modules">
    <div class="mk-section" style="padding-bottom:var(--space-10)">
      <div class="mk-wrap">
        <SectionHead :label="t.modules.label" :title="t.modules.title" />
      </div>
    </div>
    <div v-for="(key, i) in order" :key="key" :class="`mk-module ${i % 2 === 1 ? 'mk-module--alt' : ''}`">
      <div :class="`mk-module__row ${i % 2 === 1 ? 'is-reversed' : ''}`">
        <Reveal class-name="mk-module__text">
          <span class="mk-pill">{{ key.toUpperCase() }}</span>
          <h3 class="mk-module__tag">{{ t.modules.list[key].tag }}</h3>
          <p class="mk-module__desc">{{ t.modules.list[key].desc }}</p>
          <p class="mk-module__diff">{{ t.modules.list[key].diff }}</p>
        </Reveal>
        <Reveal :delay="120" class-name="mk-module__visual">
          <ModulePreviews :module="key" />
        </Reveal>
      </div>
    </div>
  </section>
</template>
