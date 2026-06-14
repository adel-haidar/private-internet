<script setup lang="ts">
import { ref } from 'vue'
import PIIcon from './PIIcon.vue'

interface Props {
  label: string
  defaultOpen?: boolean
}
const props = withDefaults(defineProps<Props>(), { defaultOpen: false })

const open = ref(props.defaultOpen)
</script>

<template>
  <div :class="['pi-collapse', open ? 'pi-collapse--open' : '']">
    <button
      type="button"
      class="pi-collapse__toggle"
      :aria-expanded="open"
      @click="open = !open"
    >
      <PIIcon name="chevronRight" :size="14" />{{ label }}
    </button>
    <div v-if="open" class="pi-collapse__body">
      <slot />
    </div>
  </div>
</template>
