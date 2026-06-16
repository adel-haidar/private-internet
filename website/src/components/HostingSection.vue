<script setup lang="ts">
import SectionHead from './SectionHead.vue'
import PIIcon from './PIIcon.vue'
import PiBadge from './PiBadge.vue'
import PiButton from './PiButton.vue'
import Reveal from './Reveal.vue'
import { scrollToId } from '@/composables/useSite'

const props = defineProps<{ t: Record<string, any> }>()
const emit = defineEmits<{ openModal: [type: 'cloud' | 'self'] }>()

function openGithub() {
  window.open(props.t.hosting.dev.url, '_blank', 'noopener')
}
</script>

<template>
  <section class="mk-section" id="hosting">
    <div class="mk-wrap">
      <SectionHead :label="t.hosting.label" :title="t.hosting.title" :body="t.hosting.body" :max-body="620" />

      <div class="mk-hosting__grid">
        <!-- Cloud -->
        <Reveal>
          <div class="mk-host">
            <div class="mk-host__chips">
              <PiBadge variant="success">{{ t.hosting.c1.chip }}</PiBadge>
            </div>
            <div class="mk-host__name">{{ t.hosting.c1.name }}</div>
            <div class="mk-host__sub">{{ t.hosting.c1.sub }}</div>
            <p class="mk-host__desc">{{ t.hosting.c1.desc }}</p>
            <ul class="mk-host__list">
              <li v-for="(it, i) in t.hosting.c1.items" :key="i">
                <span class="mk-check"><PIIcon name="check" :size="15" /></span>{{ it }}
              </li>
            </ul>
            <div class="mk-host__cta">
              <PiButton variant="primary" :block="true" icon="arrowRight" @click="emit('openModal', 'cloud')">{{ t.hosting.c1.cta }}</PiButton>
            </div>
          </div>
        </Reveal>

        <!-- Self-hosted -->
        <Reveal :delay="100">
          <div class="mk-host">
            <div class="mk-host__chips">
              <PiBadge variant="filled">{{ t.hosting.c2.chip }}</PiBadge>
            </div>
            <div class="mk-host__name">{{ t.hosting.c2.name }}</div>
            <div class="mk-host__sub">{{ t.hosting.c2.sub }}</div>
            <p class="mk-host__desc">{{ t.hosting.c2.desc }}</p>
            <ul class="mk-host__list">
              <li v-for="(it, i) in t.hosting.c2.items" :key="i">
                <span class="mk-check"><PIIcon name="check" :size="15" /></span>{{ it }}
              </li>
            </ul>
            <div class="mk-host__cta">
              <PiButton variant="primary" :block="true" @click="emit('openModal', 'self')">{{ t.hosting.c2.cta }}</PiButton>
              <PiButton variant="ghost" :block="true" @click="scrollToId('hardware')">{{ t.hosting.c2.cta2 }}</PiButton>
            </div>
          </div>
        </Reveal>

        <!-- Private hardware -->
        <Reveal :delay="200">
          <div class="mk-host mk-host--soon">
            <div class="mk-ribbon">{{ t.hosting.c3.chip }}</div>
            <div class="mk-host__chips">
              <PiBadge variant="amber">{{ t.hosting.c3.chip }}</PiBadge>
            </div>
            <div class="mk-host__name">{{ t.hosting.c3.name }}</div>
            <div class="mk-host__sub">{{ t.hosting.c3.sub }}</div>
            <p class="mk-host__desc">{{ t.hosting.c3.desc }}</p>
            <div class="mk-host__cta">
              <PiButton variant="secondary" :block="true" :disabled="true">{{ t.hosting.c3.cta }}</PiButton>
            </div>
          </div>
        </Reveal>
      </div>

      <!-- For developers banner -->
      <Reveal :delay="120">
        <div class="mk-dev">
          <div class="mk-dev__glyph" aria-hidden="true">
            <PIIcon name="terminal" :size="22" />
          </div>
          <div class="mk-dev__body">
            <div class="mk-dev__eyebrow">{{ t.hosting.dev.eyebrow }}</div>
            <div class="mk-dev__name">{{ t.hosting.dev.name }}</div>
            <p class="mk-dev__desc">{{ t.hosting.dev.desc }}</p>
            <ul class="mk-dev__list">
              <li v-for="(it, i) in t.hosting.dev.items" :key="i">
                <span class="mk-dev__ic">
                  <PIIcon :name="['branch','key','shield'][i]" :size="15" />
                </span>{{ it }}
              </li>
            </ul>
          </div>
          <div class="mk-dev__cta">
            <PiButton variant="primary" icon="github" @click="openGithub">{{ t.hosting.dev.cta }}</PiButton>
            <a class="mk-dev__link" :href="t.hosting.dev.docsUrl" target="_blank" rel="noopener">
              {{ t.hosting.dev.cta2 }}<PIIcon name="external" :size="13" />
            </a>
          </div>
        </div>
      </Reveal>
    </div>
  </section>
</template>
