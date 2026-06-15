<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import BrainPulse from './BrainPulse.vue'
import PIIcon from './PIIcon.vue'
import PiButton from './PiButton.vue'

const props = defineProps<{ t: Record<string, any> }>()
const emit = defineEmits<{ close: [] }>()

const loading = ref(false)

function submit(e: Event) {
  e.preventDefault()
  loading.value = true
  setTimeout(() => { loading.value = false; emit('close') }, 900)
}

function onKey(e: KeyboardEvent) { if (e.key === 'Escape') emit('close') }
onMounted(() => {
  document.addEventListener('keydown', onKey)
  document.body.style.overflow = 'hidden'
})
onUnmounted(() => {
  document.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})

const m = props.t.modal.self
</script>

<template>
  <div class="mk-overlay" @click.self="emit('close')">
    <div class="mk-modal" role="dialog" aria-modal="true">
      <div class="mk-modal__head">
        <div style="display:flex;align-items:center;gap:var(--space-3)">
          <BrainPulse :size="28" />
          <h2 class="mk-modal__title">{{ m.title }}</h2>
        </div>
        <button class="pi-btn pi-btn--icon" :aria-label="t.mobileMenu.close" @click="emit('close')">
          <PIIcon name="close" :size="18" />
        </button>
      </div>
      <p class="mk-modal__sub">{{ m.sub }}</p>
      <form class="mk-modal__fields" @submit="submit">
        <div class="pi-field">
          <label class="pi-label">{{ m.name }}</label>
          <div class="pi-input-wrap"><input class="pi-input" placeholder="Adel Haidar" required /></div>
        </div>
        <div class="pi-field">
          <label class="pi-label">{{ m.email }}</label>
          <div class="pi-input-wrap"><input class="pi-input" type="email" placeholder="you@yourserver.com" required /></div>
        </div>
        <div class="pi-field">
          <label class="pi-label">{{ m.url }}</label>
          <div class="pi-input-wrap">
            <input class="pi-input" type="url" :placeholder="m.urlPlaceholder" required style="direction:ltr;text-align:start" />
          </div>
        </div>
        <div class="mk-hw-note" style="margin-top:0">
          <p class="mk-hw-note__text" style="font-size:14px">{{ m.callout }}</p>
          <a href="https://github.com/private-internet/private-internet#self-hosting" target="_blank" rel="noopener" style="font-size:14px;display:inline-block;margin-top:8px">{{ m.guide }} →</a>
        </div>
        <PiButton variant="cta" :block="true" type="submit" :loading="loading" icon="arrowRight">{{ m.cta }}</PiButton>
      </form>
      <div class="mk-modal__foot">
        <a href="https://github.com/private-internet/private-internet" target="_blank" rel="noopener">{{ m.help }} →</a>
      </div>
    </div>
  </div>
</template>
