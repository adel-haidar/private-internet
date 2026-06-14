<script setup lang="ts">
import PiCard from './PiCard.vue'

interface Props {
  title: string
}
defineProps<Props>()
</script>

<template>
  <PiCard>
    <div class="pi-insight__head">
      <h3 class="pi-insight__title">{{ title }}</h3>
      <slot name="status" />
    </div>
    <slot />
    <div v-if="$slots.footer" class="pi-insight__foot">
      <slot name="footer" />
    </div>
  </PiCard>
</template>
