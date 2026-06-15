<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { registerReveal, unregisterReveal } from '@/composables/useSite'

const props = withDefaults(defineProps<{
  delay?: number
  as?: string
  className?: string
}>(), {
  delay: 0,
  as: 'div',
  className: '',
})

const el = ref<HTMLElement | null>(null)
const seen = ref(false)

const prefersReduced = typeof window !== 'undefined'
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches

let check: (() => void) | null = null
let t1: ReturnType<typeof setTimeout>
let t2: ReturnType<typeof setTimeout>

onMounted(() => {
  if (prefersReduced) {
    seen.value = true
    return
  }
  const node = el.value
  if (!node) return
  check = () => {
    const r = node.getBoundingClientRect()
    if (r.top < window.innerHeight * 0.9 && r.bottom > 0) {
      seen.value = true
      if (check) unregisterReveal(check)
    }
  }
  registerReveal(check)
  t1 = setTimeout(check, 60)
  t2 = setTimeout(check, 320)
})

onUnmounted(() => {
  if (check) unregisterReveal(check)
  clearTimeout(t1)
  clearTimeout(t2)
})
</script>

<template>
  <component
    :is="as"
    ref="el"
    :class="`reveal ${seen ? 'is-in' : ''} ${className}`"
    :style="{ transitionDelay: seen ? delay + 'ms' : '0ms' }"
  >
    <slot />
  </component>
</template>
