<script setup lang="ts">
/** A SIGNAL section: header (optional 3px accent bar + title, optional
 * "See all →") above a wrapping grid of cards (default slot). */
withDefaults(defineProps<{ title: string; accent?: boolean; seeAll?: boolean }>(), {
  accent: false,
  seeAll: false,
})
defineEmits<{ (e: 'all'): void }>()
</script>

<template>
  <div class="sec">
    <div class="sec__head">
      <span class="sec__l"><span v-if="accent" class="sec__bar" />{{ title }}</span>
      <button v-if="seeAll" class="sec__all" @click="$emit('all')">See all →</button>
    </div>
    <div class="sec__row"><slot /></div>
  </div>
</template>

<style scoped>
.sec { margin-top: 24px; }
.sec__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.sec__l { display: flex; align-items: center; gap: 8px; font-family: var(--font-display); font-weight: 600; font-size: 15px; color: var(--text-primary); }
.sec__bar { width: 3px; height: 15px; border-radius: 2px; background: var(--accent-primary); }
.sec__all { background: none; border: 0; color: var(--accent-primary); font-size: var(--text-sm); cursor: pointer; }
.sec__row { display: flex; flex-wrap: wrap; gap: 16px; padding-bottom: 6px; }
</style>
