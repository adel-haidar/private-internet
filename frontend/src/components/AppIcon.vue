<script setup lang="ts">
import { computed } from 'vue'
import { ICONS } from '../data/nav'

const props = defineProps<{ name: string }>()

const markup = computed(() => ICONS[props.name] ?? '')
</script>

<template>
  <svg
    class="app-icon"
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    stroke-width="1.4"
    stroke-linecap="square"
    stroke-linejoin="miter"
    v-html="markup"
  ></svg>
</template>

<style scoped>
.app-icon { width: 16px; height: 16px; display: block; flex: 0 0 auto; }
</style>
