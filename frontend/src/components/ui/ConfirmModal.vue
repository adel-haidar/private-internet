<script setup lang="ts">
import { watch, nextTick, onBeforeUnmount, ref } from 'vue'
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

const dialogEl = ref<HTMLElement | null>(null)
// Remember what had focus before the dialog opened, so we can restore it on close.
let prevFocus: HTMLElement | null = null

/** Visible, focusable elements inside the dialog (for the Tab trap). */
function focusables(): HTMLElement[] {
  if (!dialogEl.value) return []
  return Array.from(
    dialogEl.value.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((el) => !el.hasAttribute('disabled'))
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    emit('close')
    return
  }
  // Trap Tab focus within the dialog (WCAG 2.4.3 / 2.1.2 — no keyboard trap escape).
  if (e.key === 'Tab') {
    const items = focusables()
    if (items.length === 0) return
    const first = items[0]
    const last = items[items.length - 1]
    const active = document.activeElement as HTMLElement
    if (e.shiftKey && active === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && active === last) {
      e.preventDefault()
      first.focus()
    }
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      prevFocus = document.activeElement as HTMLElement
      window.addEventListener('keydown', onKey)
      // Move focus into the dialog once it has rendered.
      nextTick(() => focusables()[0]?.focus())
    } else {
      window.removeEventListener('keydown', onKey)
      prevFocus?.focus?.()
      prevFocus = null
    }
  },
)

onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="pi-modal-overlay"
      @click="emit('close')"
    >
      <div
        ref="dialogEl"
        class="pi-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pi-modal-title"
        :aria-describedby="body ? 'pi-modal-body' : undefined"
        @click.stop
      >
        <h2 id="pi-modal-title" class="pi-modal__title">{{ title }}</h2>
        <div v-if="body" id="pi-modal-body" class="pi-modal__body">{{ body }}</div>
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
