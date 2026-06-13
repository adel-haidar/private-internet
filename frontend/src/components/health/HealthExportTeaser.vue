<script setup lang="ts">
import PiCard from '../ui/PiCard.vue'
import PiButton from '../ui/PiButton.vue'
import PIIcon from '../ui/PIIcon.vue'
import PhoneMock from './PhoneMock.vue'

const emit = defineEmits<{
  (e: 'open', platform: 'ios' | 'android'): void
}>()
</script>

<template>
  <PiCard class="pi-guide-teaser">
    <!-- left column -->
    <div>
      <div style="display: inline-flex; align-items: center; gap: 8px; margin-bottom: var(--space-2);">
        <span style="color: var(--brain-amber); display: flex;">
          <PIIcon name="help" :size="18" />
        </span>
        <span style="font-family: var(--font-display); font-weight: 600; font-size: var(--text-md); white-space: nowrap; color: var(--text-primary);">
          Not sure how to export?
        </span>
      </div>
      <p style="font-size: var(--text-base); color: var(--text-secondary); max-width: 460px; margin-bottom: var(--space-4); line-height: 1.6;">
        Follow an illustrated, step-by-step walkthrough for getting your data off your phone — it only takes a minute.
      </p>
      <div style="display: flex; gap: var(--space-2); flex-wrap: wrap;">
        <PiButton variant="primary" icon="device" @click="emit('open', 'ios')">iPhone guide</PiButton>
        <PiButton variant="secondary" icon="watch" @click="emit('open', 'android')">Android guide</PiButton>
      </div>
    </div>

    <!-- right column: two angled phone previews -->
    <div class="pi-guide-teaser__art" aria-hidden="true">
      <!-- Android phone (back, slightly rotated left) -->
      <PhoneMock>
        <!-- Android step 1: Samsung Health home -->
        <div class="ph-nav" style="align-items: center;">
          <span class="ph-title" style="font-size: 13px;">Samsung Health</span>
          <span class="ph-ic ph-hot ph-hot--circle" style="background: #5A5A70; width: 24px; height: 24px;">⚙</span>
        </div>
        <div style="display: flex; gap: 7px; margin-bottom: 7px;">
          <div class="ph-tile">
            <div class="ph-tile__n">8,240</div>
            <div class="ph-tile__l">Steps</div>
          </div>
          <div class="ph-tile">
            <div class="ph-tile__n">72</div>
            <div class="ph-tile__l">BPM</div>
          </div>
        </div>
        <div class="ph-tile">
          <div class="ph-tile__n">7h 14m</div>
          <div class="ph-tile__l">Sleep last night</div>
        </div>
      </PhoneMock>

      <!-- iOS phone (front, slightly rotated right) -->
      <PhoneMock>
        <!-- iOS step 1: Apple Health summary -->
        <div class="ph-nav" style="align-items: flex-start;">
          <div class="ph-h1">Summary</div>
          <div class="ph-avatar ph-hot ph-hot--circle">A</div>
        </div>
        <div class="ph-grp">Favorites</div>
        <div class="ph-list">
          <div class="ph-row">
            <span class="ph-ic" style="background: #FF2D55;">♥</span>
            <span class="ph-row__t">Heart Rate</span>
            <span style="font-size: 11px; font-weight: 600; color: var(--ph-text);">72</span>
          </div>
          <div class="ph-row">
            <span class="ph-ic" style="background: #FF9500;">🦶</span>
            <span class="ph-row__t">Steps</span>
            <span style="font-size: 11px; font-weight: 600; color: var(--ph-text);">8,240</span>
          </div>
          <div class="ph-row">
            <span class="ph-ic" style="background: #5856D6;">🛏</span>
            <span class="ph-row__t">Sleep</span>
            <span style="font-size: 11px; font-weight: 600; color: var(--ph-text);">7h</span>
          </div>
        </div>
      </PhoneMock>
    </div>
  </PiCard>
</template>
