<script setup lang="ts">
import { ref } from 'vue'
import SectionHead from './SectionHead.vue'
import PIIcon from './PIIcon.vue'
import Reveal from './Reveal.vue'

defineProps<{ t: Record<string, any> }>()

const openIdx = ref(0)

function toggle(i: number) {
  openIdx.value = openIdx.value === i ? -1 : i
}
</script>

<template>
  <section class="mk-section" id="faq">
    <div class="mk-wrap mk-wrap--narrow">
      <SectionHead :label="t.faq.label" :title="t.faq.title" />
      <Reveal>
        <div class="mk-faq__list">
          <div
            v-for="(it, i) in t.faq.items"
            :key="i"
            :class="`mk-faq__item ${openIdx === i ? 'is-open' : ''}`"
          >
            <button class="mk-faq__q" :aria-expanded="openIdx === i" @click="toggle(i)">
              <span>{{ it.q }}</span>
              <span class="mk-faq__chev"><PIIcon name="chevronDown" :size="20" /></span>
            </button>
            <div class="mk-faq__a" :style="{ height: openIdx === i ? 'auto' : '0' }">
              <div class="mk-faq__a-inner">{{ it.a }}</div>
            </div>
          </div>
        </div>
      </Reveal>
    </div>
  </section>
</template>
