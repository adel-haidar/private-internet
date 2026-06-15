import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { LANG_META } from '@/locales/index'
import type { LangCode } from '@/locales/index'

export type { LangCode }

// --- Theme ---
const THEME_KEY = 'pi-site-theme'
const theme = ref<'dark' | 'light'>('dark')

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY)
  theme.value = saved === 'light' ? 'light' : 'dark'
  document.documentElement.setAttribute('data-theme', theme.value)
}

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem(THEME_KEY, theme.value)
  document.documentElement.setAttribute('data-theme', theme.value)
}

// --- Language ---
const LANG_KEY = 'pi-site-lang'
export const LANGS = ['en', 'de', 'fr', 'es', 'zh', 'ar'] as const

const lang = ref<LangCode>('en')

function applyLangToHtml(code: LangCode) {
  const meta = LANG_META[code]
  document.documentElement.lang = code
  document.documentElement.dir = meta?.dir ?? 'ltr'
}

function initLang() {
  const saved = localStorage.getItem(LANG_KEY) as LangCode
  lang.value = LANGS.includes(saved) ? saved : 'en'
  applyLangToHtml(lang.value)
}

function setLang(code: LangCode) {
  lang.value = code
  localStorage.setItem(LANG_KEY, code)
  applyLangToHtml(code)
}

// --- Scroll state ---
const isScrolled = ref(false)

// --- Reveal queue ---
type RevealCb = () => void
const revealQueue = new Set<RevealCb>()
let revealBound = false

export function registerReveal(cb: RevealCb) {
  revealQueue.add(cb)
  if (!revealBound) {
    revealBound = true
    window.addEventListener('scroll', runReveals, { passive: true })
    window.addEventListener('resize', runReveals, { passive: true })
  }
  cb()
}

export function unregisterReveal(cb: RevealCb) {
  revealQueue.delete(cb)
}

function runReveals() {
  revealQueue.forEach(cb => cb())
}

// --- scrollToId ---
export function scrollToId(id: string) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const el = document.getElementById(id)
    if (el) el.scrollIntoView()
    return
  }
  const el = document.getElementById(id)
  if (!el) return
  const top = el.getBoundingClientRect().top + window.scrollY - 60
  window.scrollTo({ top, behavior: 'smooth' })
}

// --- useSite composable ---
export function useSite() {
  let i18nLocale: ReturnType<typeof useI18n>['locale'] | null = null
  try {
    const { locale } = useI18n()
    i18nLocale = locale
  } catch {
    // outside i18n context
  }

  function onScroll() {
    isScrolled.value = window.scrollY > 60
    runReveals()
  }

  // Sync vue-i18n locale when lang changes
  watch(lang, (code) => {
    if (i18nLocale) i18nLocale.value = code
  })

  onMounted(() => {
    initTheme()
    initLang()
    if (i18nLocale) i18nLocale.value = lang.value
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
  })

  onUnmounted(() => {
    window.removeEventListener('scroll', onScroll)
  })

  function setLangAndSync(code: LangCode) {
    setLang(code)
    if (i18nLocale) i18nLocale.value = code
  }

  return { theme, lang, isScrolled, toggleTheme, setLang: setLangAndSync, scrollToId }
}

export { theme, lang, toggleTheme, setLang }
