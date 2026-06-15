import { createApp } from 'vue'
import { createI18n } from 'vue-i18n'
import App from './App.vue'
import { messages } from './locales/index'
import '@/styles/tokens.css'
import '@/styles/pi-components.css'
import '@/styles/site.css'

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages,
})

const app = createApp(App)
app.use(i18n)
app.mount('#app')
