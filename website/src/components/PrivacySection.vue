<script setup lang="ts">
import SectionHead from './SectionHead.vue'
import PIIcon from './PIIcon.vue'
import Reveal from './Reveal.vue'

defineProps<{ t: Record<string, any> }>()
</script>

<template>
  <section class="mk-section mk-privacy" id="privacy" style="background:var(--background-surface)">
    <div class="mk-wrap">
      <SectionHead :label="t.privacy.label" :title="t.privacy.title" :max-title="560" />
      <div class="mk-privacy__grid">
        <Reveal v-for="(c, i) in [
          { t:t.privacy.c1t, b:t.privacy.c1b },
          { t:t.privacy.c2t, b:t.privacy.c2b },
          { t:t.privacy.c3t, b:t.privacy.c3b },
          { t:t.privacy.c4t, b:t.privacy.c4b },
        ]" :key="i" :delay="(i % 2) * 100">
          <div class="mk-promise">
            <span class="mk-promise__icon"><PIIcon name="check" :size="22" /></span>
            <div class="mk-promise__title">{{ c.t }}</div>
            <div class="mk-promise__body">{{ c.b }}</div>
          </div>
        </Reveal>
      </div>
      <Reveal>
        <p class="mk-privacy__quote">{{ t.privacy.quote }}</p>
      </Reveal>
    </div>
  </section>
</template>
