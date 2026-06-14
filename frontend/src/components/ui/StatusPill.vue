<script setup lang="ts">
interface Props {
  kind?: 'good' | 'watch' | 'attention' | 'info'
}
withDefaults(defineProps<Props>(), { kind: 'info' })
</script>

<template>
  <span :class="['pi-status', `pi-status--${kind}`]">
    <span class="pi-status__dot" />
    <slot />
  </span>
</template>
