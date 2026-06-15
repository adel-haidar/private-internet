<script setup lang="ts">
import BrainPulse from './BrainPulse.vue'
import PIIcon from './PIIcon.vue'
import PiButton from './PiButton.vue'
import Reveal from './Reveal.vue'
import { scrollToId } from '@/composables/useSite'

defineProps<{ t: Record<string, any> }>()
const emit = defineEmits<{ start: [] }>()
</script>

<template>
  <header class="mk-hero" id="top">
    <div class="mk-hero__glow" />
    <div class="mk-hero__inner">
      <Reveal><BrainPulse :size="80" /></Reveal>
      <Reveal :delay="80">
        <div class="mk-label" style="margin-top:var(--space-6)">{{ t.hero.eyebrow }}</div>
      </Reveal>
      <Reveal :delay="160">
        <h1 class="mk-hero__title" style="margin-top:var(--space-8)">
          <span>{{ t.hero.t1 }}</span>
          <span>{{ t.hero.t2 }}</span>
          <span>{{ t.hero.t3 }}</span>
        </h1>
      </Reveal>
      <Reveal :delay="240">
        <p class="mk-hero__sub" style="margin-top:var(--space-6)">{{ t.hero.sub }}</p>
      </Reveal>
      <Reveal :delay="320">
        <div class="mk-hero__cta" style="margin-top:var(--space-10)">
          <PiButton variant="cta" icon="arrowRight" @click="emit('start')">{{ t.hero.primary }}</PiButton>
          <PiButton variant="secondary" style="height:48px" @click="scrollToId('how')">{{ t.hero.ghost }}</PiButton>
        </div>
      </Reveal>
    </div>
    <button class="mk-chevron" :aria-label="t.hero.scroll" @click="scrollToId('problem')">
      <PIIcon name="chevronDown" :size="18" />
    </button>
  </header>
</template>
