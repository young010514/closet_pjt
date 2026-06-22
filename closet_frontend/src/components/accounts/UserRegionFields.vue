<script setup>
import RegionSelector from '@/components/RegionSelector.vue'

defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
  options: {
    type: Array,
    default: () => [],
  },
  errors: {
    type: [Array, String],
    default: () => [],
  },
  maxRegions: {
    type: Number,
    default: 3,
  },
})

defineEmits(['update:modelValue'])
</script>

<template>
  <RegionSelector v-bind="$props" @update:modelValue="$emit('update:modelValue', $event)" />
</template>
