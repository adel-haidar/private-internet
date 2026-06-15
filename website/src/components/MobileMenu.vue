<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import PIIcon from './PIIcon.vue'
import PiButton from './PiButton.vue'
import { scrollToId, LANGS } from '@/composables/useSite'
import type { LangCode } from '@/composables/useSite'
import { LANG_META } from '@/locales/index'

const props = defineProps<{
  t: Record<string, any>
  lang: LangCode
  theme: 'dark' | 'light'
}>()

const emit = defineEmits<{
  close: []
  toggleTheme: []
  setLang: [code: LangCode]
  signin: []
  start: []
}>()

function go(id: string) {
  emit('close')
  setTimeout(() => scrollToId(id), 60)
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

const links = [
  { id: 'how', key: 'how' },
  { id: 'modules', key: 'modules' },
  { id: 'privacy', key: 'privacy' },
  { id: 'hosting', key: 'hosting' },
]
</script>

<template>
  <div class="mk-mobile">
    <div style="position:absolute;inset-block-start:14px;inset-inline-end:16px;display:flex;gap:var(--space-2)">
      <button class="mk-theme-toggle" aria-label="Toggle theme" @click="emit('toggleTheme')">
        <PIIcon :name="theme === 'dark' ? 'sun' : 'moon'" :size="18" />
      </button>
      <button class="pi-btn pi-btn--icon" :aria-label="t.mobileMenu.close" @click="emit('close')">
        <PIIcon name="close" :size="18" />
      </button>
    </div>
    <div class="mk-mobile__links">
      <button v-for="l in links" :key="l.id" class="mk-mobile__link" @click="go(l.id)">
        {{ t.nav[l.key] }}
      </button>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:var(--space-2);margin-top:var(--space-6)">
      <button
        v-for="code in LANGS"
        :key="code"
        :class="`mk-lang__item ${code === lang ? 'is-active' : ''}`"
        style="width:auto;border:1px solid var(--border-subtle);border-radius:var(--radius-pill)"
        @click="emit('setLang', code)"
      >
        {{ LANG_META[code].name }}
      </button>
    </div>
    <div class="mk-mobile__actions">
      <PiButton variant="secondary" :block="true" @click="() => { emit('close'); emit('signin') }">{{ t.nav.signin }}</PiButton>
      <PiButton variant="cta" :block="true" icon="arrowRight" @click="() => { emit('close'); emit('start') }">{{ t.nav.start }}</PiButton>
    </div>
  </div>
</template>
