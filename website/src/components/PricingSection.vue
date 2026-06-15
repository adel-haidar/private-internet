<script setup lang="ts">
import { ref, watch } from 'vue'
import SectionHead from './SectionHead.vue'
import PIIcon from './PIIcon.vue'
import PiButton from './PiButton.vue'
import Reveal from './Reveal.vue'
import { scrollToId } from '@/composables/useSite'

defineProps<{ t: Record<string, any> }>()

const annual = ref(localStorage.getItem('pi-billing') === 'annual')
watch(annual, (v) => localStorage.setItem('pi-billing', v ? 'annual' : 'monthly'))

function choose(plan: string) {
  try {
    sessionStorage.setItem('pi-selected-plan', plan)
    sessionStorage.setItem('pi-selected-billing', annual.value ? 'annual' : 'monthly')
  } catch {}
  scrollToId('hosting')
}

function tierVariant(kind: string, rec: boolean) {
  if (kind === 'free') return 'secondary'
  if (rec) return 'cta'
  return 'primary'
}
</script>

<template>
  <section class="mk-section" id="pricing" style="background:var(--background-surface);border-block-start:1px solid var(--border-subtle)">
    <div class="mk-wrap">
      <SectionHead :label="t.pricing.label" :max-body="620">
        <template #title>
          <template v-for="(line, i) in t.pricing.title.split('\n')" :key="i">
            <br v-if="i > 0" />{{ line }}
          </template>
        </template>
      </SectionHead>
      <!-- body under section head -->
      <p class="mk-body mk-body--center" style="max-width:620px;margin:0 auto var(--space-10)">{{ t.pricing.body }}</p>

      <!-- Billing toggle -->
      <Reveal>
        <div class="mk-pr-toggle">
          <div class="mk-bill" role="group" :aria-label="t.pricing.bill.aria">
            <button :class="`mk-bill__opt ${!annual ? 'is-active' : ''}`" :aria-pressed="!annual" @click="annual = false">{{ t.pricing.bill.monthly }}</button>
            <button :class="`mk-bill__opt ${annual ? 'is-active' : ''}`" :aria-pressed="annual" @click="annual = true">
              {{ t.pricing.bill.annual }}<span class="mk-bill__save">{{ t.pricing.bill.save }}</span>
            </button>
          </div>
        </div>
      </Reveal>

      <!-- Annual banner -->
      <div :class="`mk-pr-banner ${annual ? '' : 'is-hidden'}`">
        <span>{{ t.pricing.banner }}</span>
      </div>

      <!-- Tiers -->
      <div class="mk-pr-grid">
        <!-- Free -->
        <Reveal>
          <div class="mk-pr-card">
            <div class="mk-pr-card__name">{{ t.pricing.tiers.free.name }}</div>
            <div class="mk-pr-price">
              <span class="mk-pr-price__amt">{{ t.pricing.tiers.free.price }}</span>
              <span class="mk-pr-price__per">{{ t.pricing.tiers.free.per }}</span>
            </div>
            <p class="mk-pr-tag">{{ t.pricing.tiers.free.tagline }}</p>
            <div class="mk-pr-div" />
            <ul class="mk-pr-list">
              <li v-for="(it, i) in t.pricing.tiers.free.inc" :key="i">
                <span class="mk-pr-check"><PIIcon name="check" :size="15" /></span>{{ it }}
              </li>
            </ul>
            <ul class="mk-pr-list mk-pr-list--no">
              <li v-for="(it, i) in t.pricing.tiers.free.exc" :key="i">
                <span class="mk-pr-x" aria-hidden="true">×</span>{{ it }}
              </li>
            </ul>
            <div class="mk-pr-cta">
              <PiButton variant="secondary" :block="true" @click="choose('free')">{{ t.pricing.tiers.free.cta }}</PiButton>
              <p class="mk-pr-note">{{ t.pricing.tiers.free.note }}</p>
            </div>
          </div>
        </Reveal>

        <!-- Creator (recommended) -->
        <Reveal :delay="80">
          <div class="mk-pr-card mk-pr-card--rec">
            <span class="mk-pr-badge">{{ t.pricing.tiers.creator.badge }}</span>
            <div class="mk-pr-card__name">{{ t.pricing.tiers.creator.name }}</div>
            <div class="mk-pr-price">
              <span class="mk-pr-price__amt">{{ annual ? t.pricing.tiers.creator.priceA : t.pricing.tiers.creator.priceM }}</span>
              <span class="mk-pr-price__per">{{ t.pricing.tiers.creator.per }}</span>
            </div>
            <div :class="`mk-pr-price__annual ${annual ? '' : 'is-hidden'}`">
              <span class="mk-pr-price__billed">{{ t.pricing.tiers.creator.billed }}</span>
              <span class="mk-pr-save">{{ t.pricing.tiers.creator.save }}</span>
            </div>
            <p class="mk-pr-tag">{{ t.pricing.tiers.creator.tagline }}</p>
            <div class="mk-pr-div" />
            <ul class="mk-pr-list">
              <li v-for="(it, i) in t.pricing.tiers.creator.inc" :key="i">
                <span class="mk-pr-check"><PIIcon name="check" :size="15" /></span>{{ it }}
              </li>
            </ul>
            <ul class="mk-pr-list mk-pr-list--no">
              <li v-for="(it, i) in t.pricing.tiers.creator.exc" :key="i">
                <span class="mk-pr-x" aria-hidden="true">×</span>{{ it }}
              </li>
            </ul>
            <div class="mk-pr-cta">
              <PiButton variant="cta" :block="true" @click="choose('creator')">{{ t.pricing.tiers.creator.cta }}</PiButton>
              <p class="mk-pr-note">{{ t.pricing.tiers.creator.note }}</p>
            </div>
          </div>
        </Reveal>

        <!-- Studio -->
        <Reveal :delay="160">
          <div class="mk-pr-card">
            <div class="mk-pr-card__name">{{ t.pricing.tiers.studio.name }}</div>
            <div class="mk-pr-price">
              <span class="mk-pr-price__amt">{{ annual ? t.pricing.tiers.studio.priceA : t.pricing.tiers.studio.priceM }}</span>
              <span class="mk-pr-price__per">{{ t.pricing.tiers.studio.per }}</span>
            </div>
            <div :class="`mk-pr-price__annual ${annual ? '' : 'is-hidden'}`">
              <span class="mk-pr-price__billed">{{ t.pricing.tiers.studio.billed }}</span>
              <span class="mk-pr-save">{{ t.pricing.tiers.studio.save }}</span>
            </div>
            <p class="mk-pr-tag">{{ t.pricing.tiers.studio.tagline }}</p>
            <div class="mk-pr-div" />
            <ul class="mk-pr-list">
              <li v-for="(it, i) in t.pricing.tiers.studio.inc" :key="i">
                <span class="mk-pr-check"><PIIcon name="check" :size="15" /></span>{{ it }}
              </li>
            </ul>
            <div class="mk-pr-cta">
              <PiButton variant="primary" :block="true" @click="choose('studio')">{{ t.pricing.tiers.studio.cta }}</PiButton>
              <p class="mk-pr-note">{{ t.pricing.tiers.studio.note }}</p>
            </div>
          </div>
        </Reveal>
      </div>

      <!-- Generated callout -->
      <Reveal>
        <div class="mk-pr-gen">
          <div class="mk-pr-gen__title">{{ t.pricing.genTitle }}</div>
          <p class="mk-pr-gen__body">{{ t.pricing.genBody }}</p>
        </div>
      </Reveal>

      <!-- Self-hosted note -->
      <Reveal>
        <div class="mk-pr-self">
          <div class="mk-pr-self__title">{{ t.pricing.selfTitle }}</div>
          <p class="mk-pr-self__body">{{ t.pricing.selfBody }}</p>
          <PiButton variant="ghost" @click="scrollToId('hardware')">{{ t.pricing.selfCta }}</PiButton>
        </div>
      </Reveal>

      <!-- Pricing FAQ -->
      <Reveal>
        <div class="mk-pr-faq">
          <div v-for="(q, i) in t.pricing.faq" :key="i" class="mk-pr-faq__item">
            <div class="mk-pr-faq__q">{{ q.q }}</div>
            <p class="mk-pr-faq__a">{{ q.a }}</p>
          </div>
        </div>
      </Reveal>

      <Reveal>
        <p class="mk-pr-eur">{{ t.pricing.eur }}</p>
      </Reveal>
    </div>
  </section>
</template>
