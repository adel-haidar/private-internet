<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import BrainPulse from './BrainPulse.vue'
import PIIcon from './PIIcon.vue'
import PiButton from './PiButton.vue'
import { scrollToId } from '@/composables/useSite'
import { LANGS, LANG_META } from '@/locales/index'
import type { LangCode } from '@/locales/index'

function scrollTop() { window.scrollTo({ top: 0, behavior: 'smooth' }) }
function langName(code: string) { return LANG_META[code as LangCode]?.name ?? code }

const props = defineProps<{
  t: Record<string, any>
  lang: LangCode
  scrolled: boolean
  theme: 'dark' | 'light'
}>()

const emit = defineEmits<{
  toggleTheme: []
  setLang: [code: LangCode]
  openMobile: []
  signin: []
  start: []
}>()

const langOpen = ref(false)
const langRef = ref<HTMLElement | null>(null)

function onDocClick(e: MouseEvent) {
  if (langRef.value && !langRef.value.contains(e.target as Node)) langOpen.value = false
}

onMounted(() => document.addEventListener('mousedown', onDocClick))
onUnmounted(() => document.removeEventListener('mousedown', onDocClick))

const links = [
  { id: 'how', key: 'how' },
  { id: 'modules', key: 'modules' },
  { id: 'privacy', key: 'privacy' },
  { id: 'hosting', key: 'hosting' },
]
</script>

<template>
  <nav :class="`mk-nav ${scrolled ? 'is-scrolled' : ''}`">
    <div class="mk-nav__inner">
      <div class="mk-brand" style="cursor:pointer" @click="scrollTop">
        <BrainPulse :size="14" />
        <span class="mk-brand__name">Private Internet</span>
      </div>

      <div class="mk-nav__links">
        <button v-for="l in links" :key="l.id" class="mk-nav__link" @click="scrollToId(l.id)">
          {{ t.nav[l.key] }}
        </button>
      </div>

      <div class="mk-nav__right">
        <!-- Language picker -->
        <div class="mk-lang" ref="langRef">
          <button class="mk-lang__btn" :aria-expanded="langOpen" aria-haspopup="true" @click="langOpen = !langOpen">
            <PIIcon name="globe" :size="16" />
            <span style="text-transform:uppercase">{{ lang }}</span>
            <PIIcon name="chevronDown" :size="13" />
          </button>
          <div v-if="langOpen" class="mk-lang__menu" role="menu">
            <button
              v-for="code in LANGS"
              :key="code"
              :class="`mk-lang__item ${code === lang ? 'is-active' : ''}`"
              role="menuitem"
              @click="emit('setLang', code); langOpen = false"
            >
              <span>{{ langName(code) }}</span>
              <span class="mk-lang__code">{{ code }}</span>
            </button>
          </div>
        </div>

        <button class="mk-theme-toggle" aria-label="Toggle theme" @click="emit('toggleTheme')">
          <PIIcon :name="theme === 'dark' ? 'sun' : 'moon'" :size="18" />
        </button>

        <PiButton variant="ghost" size="compact" @click="emit('signin')">{{ t.nav.signin }}</PiButton>
        <PiButton variant="primary" size="compact" @click="emit('start')">{{ t.nav.start }}</PiButton>

        <button class="pi-btn pi-btn--icon mk-hamburger" aria-label="Menu" @click="emit('openMobile')">
          <PIIcon name="drag" :size="18" />
        </button>
      </div>
    </div>
  </nav>
</template>
