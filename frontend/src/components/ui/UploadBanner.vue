<script setup lang="ts">
import PIIcon from './PIIcon.vue'

interface Props {
  tone?: 'amber' | 'info'
  icon: string
  title: string
  intro?: string
  items?: string[]
  note?: string
}
withDefaults(defineProps<Props>(), { tone: 'amber', items: () => [] })
</script>

<template>
  <div :class="['pi-banner', `pi-banner--${tone}`]">
    <div class="pi-banner__head">
      <span class="pi-banner__ic"><PIIcon :name="icon" :size="20" /></span>
      <span class="pi-banner__title">{{ title }}</span>
    </div>
    <p v-if="intro" class="pi-banner__intro">{{ intro }}</p>
    <ul v-if="items.length" class="pi-banner__list">
      <li v-for="(it, i) in items" :key="i">{{ it }}</li>
    </ul>
    <p v-if="note" class="pi-banner__note">{{ note }}</p>
    <div v-if="$slots.actions" class="pi-banner__actions">
      <slot name="actions" />
    </div>
  </div>
</template>
