<script setup lang="ts">
import PIIcon from './PIIcon.vue'

const props = withDefaults(defineProps<{
  variant?: 'primary' | 'cta' | 'secondary' | 'ghost' | 'danger'
  size?: 'compact' | 'default'
  block?: boolean
  icon?: string
  iconRight?: string
  loading?: boolean
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
}>(), {
  variant: 'primary',
  size: 'default',
  block: false,
  loading: false,
  disabled: false,
  type: 'button',
})

const emit = defineEmits<{ click: [e: MouseEvent] }>()

const cls = () => {
  const c = ['pi-btn', `pi-btn--${props.variant}`]
  if (props.size === 'compact') c.push('pi-btn--compact')
  if (props.block) c.push('pi-btn--block')
  return c.join(' ')
}
</script>

<template>
  <button
    :class="cls()"
    :disabled="disabled || loading"
    :type="type"
    @click="emit('click', $event)"
  >
    <span v-if="loading" class="pi-btn__spinner" aria-hidden="true" />
    <PIIcon v-if="!loading && icon" :name="icon" :size="16" />
    <slot v-if="!loading" />
    <PIIcon v-if="!loading && iconRight" :name="iconRight" :size="16" />
  </button>
</template>
