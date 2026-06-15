<script setup lang="ts">
import Reveal from './Reveal.vue'

withDefaults(defineProps<{
  label?: string
  title?: string
  body?: string
  center?: boolean
  maxTitle?: number
  maxBody?: number
}>(), {
  center: true,
  maxTitle: 720,
  maxBody: 600,
})
</script>

<template>
  <div :style="{ textAlign: center ? 'center' : 'start', marginBottom: 'var(--space-12)' }">
    <Reveal v-if="label">
      <div class="mk-label">{{ label }}</div>
    </Reveal>
    <Reveal :delay="60">
      <h2 class="mk-title" :style="{ maxWidth: maxTitle + 'px', margin: center ? '16px auto 0' : '16px 0 0' }">
        <slot name="title">{{ title }}</slot>
      </h2>
    </Reveal>
    <Reveal v-if="body" :delay="120">
      <p class="mk-body" :style="{ maxWidth: maxBody + 'px', margin: center ? '20px auto 0' : '20px 0 0', textAlign: center ? 'center' : 'start' }">{{ body }}</p>
    </Reveal>
  </div>
</template>
