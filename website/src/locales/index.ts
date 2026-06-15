import en from './en'
import de from './de'
import fr from './fr'
import es from './es'
import zh from './zh'
import ar from './ar'

export const messages = { en, de, fr, es, zh, ar }

export type LangCode = 'en' | 'de' | 'fr' | 'es' | 'zh' | 'ar'

export const LANGS = ['en', 'de', 'fr', 'es', 'zh', 'ar'] as const

export const LANG_META: Record<LangCode, { name: string; dir: 'ltr' | 'rtl' }> = {
  en: { name: 'English', dir: 'ltr' },
  de: { name: 'Deutsch', dir: 'ltr' },
  fr: { name: 'Français', dir: 'ltr' },
  es: { name: 'Español', dir: 'ltr' },
  zh: { name: '中文', dir: 'ltr' },
  ar: { name: 'العربية', dir: 'rtl' },
}
