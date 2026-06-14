<script setup lang="ts">
import { watch, onBeforeUnmount } from 'vue'
import PiButton from './PiButton.vue'

interface Props {
  open: boolean
  title: string
  body?: string
  confirmLabel?: string
  danger?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  confirmLabel: 'Confirm',
  danger: false,
})

const emit = defineEmits<{ close: []; confirm: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) window.addEventListener('keydown', onKey)
    else window.removeEventListener('keydown', onKey)
  },
)

onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="pi-modal-overlay"
      role="dialog"
      aria-modal="true"
      @click="emit('close')"
    >
      <div class="pi-modal" @click.stop>
        <div class="pi-modal__title">{{ title }}</div>
        <div v-if="body" class="pi-modal__body">{{ body }}</div>
        <div class="pi-modal__actions">
          <PiButton variant="secondary" @click="emit('close')">Cancel</PiButton>
          <PiButton :variant="danger ? 'danger' : 'primary'" @click="emit('confirm')">
            {{ confirmLabel }}
          </PiButton>
        </div>
      </div>
    </div>
  </Teleport>
</template>
