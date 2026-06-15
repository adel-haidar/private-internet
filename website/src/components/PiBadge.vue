<script setup lang="ts">
import PIIcon from './PIIcon.vue'

withDefaults(defineProps<{
  variant?: 'success' | 'filled' | 'amber' | 'outlined' | 'warning' | 'danger'
  icon?: string
}>(), {
  variant: 'filled',
})
</script>

<template>
  <span :class="`pi-badge pi-badge--${variant}`">
    <PIIcon v-if="icon" :name="icon" :size="12" />
    <slot />
  </span>
</template>
