<script setup lang="ts">
import PIIcon from './PIIcon.vue'

interface Props {
  modelValue?: string
  icon?: string
  error?: string
  placeholder?: string
  type?: string
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  disabled: false,
})

const emit = defineEmits<{
  'update:modelValue': [v: string]
}>()

// Forward id/name/autocomplete/etc. to the <input> itself (not the wrapper),
// so a sibling <label for="…"> resolves to the real field.
defineOptions({ inheritAttrs: false })

// Stable id so the error text can be linked to the input via aria-describedby.
const errorId = `pi-input-err-${Math.random().toString(36).slice(2, 9)}`
</script>

<template>
  <div :class="['pi-input-wrap', icon ? 'has-icon' : '']">
    <span v-if="icon" class="pi-input__icon" aria-hidden="true">
      <PIIcon :name="icon" :size="16" />
    </span>
    <input
      :class="['pi-input', error ? 'pi-input--error' : '']"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="error ? errorId : undefined"
      v-bind="$attrs"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
  </div>
  <p v-if="error" :id="errorId" class="pi-field__error" role="alert">{{ error }}</p>
</template>
