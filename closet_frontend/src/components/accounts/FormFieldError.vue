<script setup>
import { computed } from 'vue'

const props = defineProps({
  errors: {
    type: [Array, String],
    default: () => [],
  },
})

const messages = computed(() => {
  if (Array.isArray(props.errors)) return props.errors.filter(Boolean)
  return props.errors ? [props.errors] : []
})
</script>

<template>
  <p v-if="messages.length" class="field-error" role="alert">
    <span v-for="message in messages" :key="message">{{ message }}</span>
  </p>
</template>
