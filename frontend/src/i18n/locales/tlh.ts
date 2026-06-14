/**
 * Klingon (tlhIngan Hol) — best-effort, Latin transliteration (written LTR).
 *
 * Only the terms with reasonably authentic Klingon vocabulary are provided
 * (yab = mind, Hol = language, Qapla' = success). Every other key falls back to
 * English automatically via the i18n lookup, so the UI stays usable.
 */
export const tlh = {
  nav: {
    brain: 'yablIj', // "your mind"
  },
  dashboard: {
    brainTitle: 'yab', // mind / brain
  },
  settings: {
    profile: {
      language: 'Hol', // language
    },
    toast: {
      profileUpdated: "Qapla'!", // success / triumph
      photoUpdated: "Qapla'!",
      languageUpdated: "Qapla'!",
      exportDownloaded: "Qapla'!",
    },
  },
}
