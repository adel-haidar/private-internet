<script setup lang="ts">
/**
 * BrainBanner — dismissible "feed your brain" nudge shown at the top of the
 * four content views (Pulse, Signal, Stories, Aria). Dismissal is persisted
 * globally in localStorage under 'pi-brain-banner-dismissed' so the banner
 * only ever needs to be closed once.
 *
 * Styled with Calm Intelligence tokens. Uses the existing BrainPulse component
 * for the signature amber animation. No card shadow — depth via bg step +
 * border only.
 */
import { ref } from 'vue'
import { useI18n } from '../i18n/index'
import BrainPulse from './ui/BrainPulse.vue'

const STORAGE_KEY = 'pi-brain-banner-dismissed'

const { t } = useI18n()

const dismissed = ref<boolean>(localStorage.getItem(STORAGE_KEY) === '1')

function dismiss() {
  dismissed.value = true
  localStorage.setItem(STORAGE_KEY, '1')
}
</script>

<template>
  <Transition name="brain-banner">
    <div v-if="!dismissed" class="brain-banner" role="note" aria-label="Brain tip">
      <BrainPulse :size="20" slow class="brain-banner__pulse" />

      <p class="brain-banner__text">
        {{ t('brainBanner.message') }}
        <RouterLink to="/memory" class="brain-banner__link">{{ t('brainBanner.cta') }}</RouterLink>
      </p>

      <button
        class="brain-banner__close"
        :aria-label="t('brainBanner.dismiss')"
        @click="dismiss"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
          <path d="M1 1l12 12M13 1L1 13" />
        </svg>
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.brain-banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px var(--space-4);
  margin-bottom: var(--space-4);
  background: var(--brain-amber-surface);
  border: 1px solid color-mix(in srgb, var(--brain-amber) 30%, transparent);
  border-radius: var(--radius-md);
}

.brain-banner__pulse {
  flex: 0 0 auto;
}

.brain-banner__text {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-family: var(--font-body);
  line-height: 1.5;
}

.brain-banner__link {
  margin-inline-start: 6px;
  color: var(--brain-amber);
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
}

.brain-banner__link:hover {
  text-decoration: underline;
  text-decoration-color: color-mix(in srgb, var(--brain-amber) 60%, transparent);
  text-underline-offset: 2px;
}

.brain-banner__close {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  transition: background-color 0.15s, color 0.15s;
}

.brain-banner__close:hover {
  background: color-mix(in srgb, var(--brain-amber) 12%, transparent);
  color: var(--text-secondary);
}

/* Slide-down enter / fade-out leave */
.brain-banner-enter-active {
  animation: pi-slide-down 0.2s var(--ease);
}
.brain-banner-leave-active {
  transition: opacity 0.15s var(--ease), transform 0.15s var(--ease), margin-bottom 0.15s var(--ease), padding 0.15s var(--ease), height 0.15s var(--ease);
  overflow: hidden;
}
.brain-banner-leave-to {
  opacity: 0;
  transform: translateY(-4px);
  margin-bottom: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>
