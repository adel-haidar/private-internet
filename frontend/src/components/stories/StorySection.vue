<script setup lang="ts">
/**
 * StorySection — horizontal scroll row with optional accent bar + "See all" link.
 */
defineProps<{
  title: string
  accent?: boolean
  onAll?: (() => void) | null
}>()

const emit = defineEmits<{
  (e: 'all'): void
}>()
</script>

<template>
  <section class="st-sec">
    <div class="st-sechead">
      <span class="st-sechead__l">
        <span v-if="accent" class="st-sechead__bar" />
        {{ title }}
      </span>
      <button v-if="onAll" class="st-sechead__all" @click="emit('all')">See all →</button>
    </div>
    <div class="st-row">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.st-sec { margin-top: var(--space-8); }
.st-sechead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}
.st-sechead__l {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--text-md);
}
.st-sechead__bar {
  width: 3px;
  height: 18px;
  border-radius: 2px;
  background: var(--accent-primary);
  flex: 0 0 auto;
}
.st-sechead__all {
  font-size: var(--text-sm);
  color: var(--accent-primary);
  background: none;
  border: none;
  cursor: pointer;
}
.st-row {
  display: flex;
  gap: var(--space-4);
  overflow-x: auto;
  padding-bottom: var(--space-2);
  scroll-snap-type: x proximity;
}
.st-row::-webkit-scrollbar { height: 8px; }
</style>
