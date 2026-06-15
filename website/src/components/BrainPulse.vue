<script setup lang="ts">
const props = withDefaults(defineProps<{
  size?: number
  slow?: boolean
}>(), {
  size: 16,
  slow: false,
})

const k = props.size / 16
const r = [6 * k, 9 * k, 7 * k, 11 * k]
const dot = Math.max(2, Math.round(2.4 * k))
const styleVars = {
  width: props.size + 'px',
  height: props.size + 'px',
  '--bp-dot': dot + 'px',
  '--r1': r[0] + 'px',
  '--r2': r[1] + 'px',
  '--r3': r[2] + 'px',
  '--r4': r[3] + 'px',
}

function orbitStyle(n: number) {
  if (!props.slow) return undefined
  return { animationDuration: (24 + n * 4) + 's' }
}
</script>

<template>
  <span class="brain-pulse" :style="styleVars" aria-hidden="true">
    <span class="bp-center" />
    <span v-for="n in [1,2,3,4]" :key="n" :class="`bp-orbit bp-o${n}`" :style="orbitStyle(n)">
      <span class="bp-dot" />
    </span>
  </span>
</template>
