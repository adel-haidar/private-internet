/**
 * Lightweight, dependency-free i18n (mirrors useTheme's singleton pattern).
 *
 * - `locale` is a shared ref; reading it inside t() makes templates re-render on
 *   language change.
 * - t(key, params) does dot-path lookup with {param} interpolation and falls
 *   back to English, then the raw key, so a missing translation never shows a
 *   blank or a crash.
 * - Sets <html lang> and <html dir> (rtl for Arabic) on every change.
 * - Persists to localStorage; the account's language_preference is applied on
 *   load (see App.vue) so the choice follows the user across devices.
 */
import { ref } from 'vue'
import { en } from './locales/en'
import { de } from './locales/de'
import { es } from './locales/es'
import { fr } from './locales/fr'
import { sv } from './locales/sv'
import { ru } from './locales/ru'
import { zh } from './locales/zh'
import { ar } from './locales/ar'

export type LocaleCode = 'en' | 'de' | 'es' | 'fr' | 'sv' | 'ru' | 'zh' | 'ar'

export interface LocaleMeta { code: LocaleCode; label: string; rtl?: boolean }

// Order shown in the language picker. `label` is each language's endonym.
export const LOCALES: LocaleMeta[] = [
  { code: 'en', label: 'English' },
  { code: 'de', label: 'Deutsch' },
  { code: 'es', label: 'Español' },
  { code: 'fr', label: 'Français' },
  { code: 'sv', label: 'Svenska' },
  { code: 'ru', label: 'Русский' },
  { code: 'zh', label: '中文' },
  { code: 'ar', label: 'العربية', rtl: true },
]

const MESSAGES: Record<LocaleCode, Record<string, unknown>> = { en, de, es, fr, sv, ru, zh, ar }
const RTL = new Set<LocaleCode>(['ar'])
const STORAGE_KEY = 'pi-locale'

function isLocale(code: string): code is LocaleCode {
  return code in MESSAGES
}

function detect(): LocaleCode {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved && isLocale(saved)) return saved
  const nav = (navigator.language || 'en').slice(0, 2).toLowerCase()
  return isLocale(nav) ? nav : 'en'
}

const locale = ref<LocaleCode>(detect())

function apply(code: LocaleCode): void {
  const el = document.documentElement
  el.lang = code
  el.dir = RTL.has(code) ? 'rtl' : 'ltr'
}
apply(locale.value)

function lookup(messages: Record<string, unknown>, key: string): unknown {
  return key.split('.').reduce<unknown>(
    (o, k) => (o && typeof o === 'object' ? (o as Record<string, unknown>)[k] : undefined),
    messages,
  )
}

function t(key: string, params?: Record<string, string | number>): string {
  // Read locale.value so this is a render dependency → re-renders on setLocale.
  const active = locale.value
  const raw = lookup(MESSAGES[active], key) ?? lookup(MESSAGES.en, key) ?? key
  if (typeof raw !== 'string') return key
  if (!params) return raw
  return raw.replace(/\{(\w+)\}/g, (_, k: string) => (k in params ? String(params[k]) : `{${k}}`))
}

function setLocale(code: string): void {
  if (!isLocale(code)) return
  locale.value = code
  apply(code)
  localStorage.setItem(STORAGE_KEY, code)
}

export function useI18n() {
  return { locale, t, setLocale, locales: LOCALES }
}
