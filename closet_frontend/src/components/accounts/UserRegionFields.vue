<script setup>
import { computed, ref } from 'vue'

import FormFieldError from './FormFieldError.vue'

const props = defineProps({
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
})

const emit = defineEmits(['update:modelValue'])
const selectedRegionId = ref('')
const localError = ref('')

const selectedRegions = computed(() => props.modelValue || [])
const hasOptions = computed(() => props.options.length > 0)

function regionLabel(regionId) {
  const option = props.options.find((item) => Number(item.id ?? item.pk) === Number(regionId))
  if (!option) return `지역 ${regionId}`

  const parts = [option.sido, option.sigungu, option.dong].filter(Boolean)
  return option.full_name || parts.join(' ') || `지역 ${regionId}`
}

function addRegion() {
  localError.value = ''
  const regionId = Number(selectedRegionId.value)
  if (!regionId) return

  if (selectedRegions.value.length >= 3) {
    localError.value = '지역은 최대 3개까지 선택할 수 있습니다.'
    return
  }

  if (selectedRegions.value.some((item) => Number(item.region_id) === regionId)) {
    localError.value = '같은 지역을 중복해서 선택할 수 없습니다.'
    return
  }

  emitRegions([...selectedRegions.value, { region_id: regionId }])
  selectedRegionId.value = ''
}

function removeRegion(index) {
  localError.value = ''
  emitRegions(selectedRegions.value.filter((_, currentIndex) => currentIndex !== index))
}

function moveRegion(from, to) {
  if (to < 0 || to >= selectedRegions.value.length) return
  localError.value = ''
  const next = [...selectedRegions.value]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  emitRegions(next)
}

function emitRegions(items) {
  emit(
    'update:modelValue',
    items.map((item, index) => ({
      region_id: Number(item.region_id),
      priority: index + 1,
    })),
  )
}
</script>

<template>
  <section class="form-section region-box">
    <div class="section-heading">
      <h2>지역 선택</h2>
      <span>{{ selectedRegions.length }}/3</span>
    </div>

    <p v-if="!hasOptions" class="muted-text">
      현재 지역 목록 JSON API가 없어 지역 설정 없이 가입합니다.
    </p>

    <div v-else class="inline-controls">
      <label class="sr-only" for="signup-region-select">지역</label>
      <select id="signup-region-select" v-model="selectedRegionId">
        <option value="">지역을 선택해 주세요</option>
        <option
          v-for="option in options"
          :key="option.id ?? option.pk"
          :value="option.id ?? option.pk"
        >
          {{ option.full_name || [option.sido, option.sigungu, option.dong].filter(Boolean).join(' ') }}
        </option>
      </select>
      <button type="button" class="button button--secondary" @click="addRegion">추가</button>
    </div>

    <ul v-if="selectedRegions.length" class="selected-list">
      <li v-for="(item, index) in selectedRegions" :key="item.region_id" class="selected-item">
        <span>{{ index + 1 }}순위 · {{ regionLabel(item.region_id) }}</span>
        <span class="button-group">
          <button type="button" class="mini-button" :disabled="index === 0" @click="moveRegion(index, index - 1)">
            위로
          </button>
          <button
            type="button"
            class="mini-button"
            :disabled="index === selectedRegions.length - 1"
            @click="moveRegion(index, index + 1)"
          >
            아래로
          </button>
          <button type="button" class="mini-button" @click="removeRegion(index)">삭제</button>
        </span>
      </li>
    </ul>

    <p v-if="localError" class="field-error" role="alert">{{ localError }}</p>
    <FormFieldError :errors="errors" />
  </section>
</template>
