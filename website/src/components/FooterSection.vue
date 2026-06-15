<script setup lang="ts">
import BrainPulse from './BrainPulse.vue'
import PIIcon from './PIIcon.vue'
import { LANGS, LANG_META } from '@/locales/index'
import type { LangCode } from '@/locales/index'

function langName(code: string) { return LANG_META[code as LangCode]?.name ?? code }

defineProps<{
  t: Record<string, any>
  lang: LangCode
  theme: 'dark' | 'light'
}>()

const emit = defineEmits<{
  setLang: [code: LangCode]
  toggleTheme: []
}>()
</script>

<template>
  <footer class="mk-footer">
    <div class="mk-footer__cols">
      <div>
        <div class="mk-brand">
          <BrainPulse :size="16" />
          <span class="mk-brand__name">Private Internet</span>
        </div>
        <p class="mk-footer__tag">{{ t.footer.tagline }}</p>
        <button class="mk-theme-toggle" aria-label="Toggle theme" style="border:1px solid var(--border-subtle)" @click="emit('toggleTheme')">
          <PIIcon :name="theme === 'dark' ? 'sun' : 'moon'" :size="16" />
        </button>
      </div>
      <div>
        <div class="mk-footer__h">{{ t.footer.product }}</div>
        <div class="mk-footer__links">
          <button v-for="(l, i) in t.footer.productLinks" :key="i" class="mk-footer__link">{{ l }}</button>
        </div>
      </div>
      <div>
        <div class="mk-footer__h">{{ t.footer.company }}</div>
        <div class="mk-footer__links">
          <button v-for="(l, i) in t.footer.companyLinks" :key="i" class="mk-footer__link">{{ l }}</button>
        </div>
      </div>
      <div>
        <div class="mk-footer__h">{{ t.footer.languages }}</div>
        <div class="mk-footer__links">
          <button
            v-for="code in LANGS"
            :key="code"
            :class="`mk-footer__link ${code === lang ? 'is-active' : ''}`"
            @click="emit('setLang', code)"
          >
            {{ langName(code) }}
          </button>
        </div>
      </div>
    </div>
    <div class="mk-footer__bottom">{{ t.footer.copyright }}</div>
  </footer>
</template>
