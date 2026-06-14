<script setup lang="ts">
/** The full-width editorial hero shared by PULSE and SIGNAL: real image
 * full-bleed (or a seeded wash), a bottom scrim, absolute top-left/top-right
 * slots, an optional centre slot (play button), and the title + meta body. */
import { computed } from 'vue'
import { seededHero } from './seeded'

const props = defineProps<{
  seed: string
  image?: string | null
  title: string
  metaName: string
  metaTrailing: string
}>()
defineEmits<{ (e: 'click'): void }>()

const bg = computed(() =>
  props.image
    ? { backgroundImage: `url(${props.image})`, backgroundSize: 'cover', backgroundPosition: 'center' }
    : seededHero(props.seed),
)
</script>

<template>
  <div class="feat" @click="$emit('click')">
    <div class="feat__bg" :style="bg" />
    <div class="feat__scrim" />
    <div class="feat__top feat__top--l"><slot name="topLeft" /></div>
    <div class="feat__top feat__top--r"><slot name="topRight" /></div>
    <div v-if="$slots.center" class="feat__center"><slot name="center" /></div>
    <div class="feat__body">
      <div class="feat__title">{{ title }}</div>
      <div class="feat__meta">
        <span class="feat__name">{{ metaName }}</span>
        <span class="feat__trail t-mono">{{ metaTrailing }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.feat {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  min-height: 240px;
  background: var(--background-raised);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}
.feat__bg { position: absolute; inset: 0; }
.feat__scrim {
  position: absolute; inset: 0;
  background: linear-gradient(to top, rgba(12,12,20,0.92) 0%, rgba(12,12,20,0.45) 45%, rgba(12,12,20,0) 100%);
}
.feat__top { position: absolute; top: 14px; z-index: 2; }
.feat__top--l { left: 14px; }
.feat__top--r { right: 14px; }
.feat__center { position: absolute; inset: 0; display: grid; place-items: center; z-index: 2; }
.feat__body { position: relative; z-index: 2; padding: 18px; }
.feat__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 22px;
  line-height: 1.25;
  color: #fff;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.feat__meta { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.feat__name { font-family: var(--font-display); font-weight: 500; font-size: var(--text-sm); color: rgba(255,255,255,0.85); }
.feat__trail { font-family: var(--font-mono); font-size: var(--text-xs); color: rgba(255,255,255,0.72); }
</style>
