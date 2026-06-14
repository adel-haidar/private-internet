<script setup lang="ts">
/** Like / dislike / open action — fills with its colour for 300ms on tap (and
 * stays filled when [active]). */
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{ label: string; color: string; active?: boolean; icon?: 'up' | 'down' | 'open' }>(),
  { active: false, icon: 'up' },
)
const emit = defineEmits<{ (e: 'click'): void }>()

const flash = ref(false)
function onClick(e: MouseEvent) {
  e.stopPropagation()
  flash.value = true
  setTimeout(() => (flash.value = false), 300)
  emit('click')
}
</script>

<template>
  <button
    class="vb"
    :class="{ 'vb--on': active || flash }"
    :style="{ '--vb': color }"
    @click="onClick"
  >
    <svg v-if="icon === 'up'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
    <svg v-else-if="icon === 'down'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>
    <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17L17 7M7 7h10v10"/></svg>
    {{ label }}
  </button>
</template>

<style scoped>
.vb {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 36px;
  padding: 0 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.3s, color 0.3s, border-color 0.3s;
}
.vb--on { background: var(--vb); border-color: var(--vb); color: #fff; }
</style>
