<script setup>
import { computed, onMounted, ref } from 'vue'

import { normalizeApiError } from '@/api/accounts'
import { getDongs, getSigungus, getSidos } from '@/api/regions'

import FormFieldError from '@/components/accounts/FormFieldError.vue'

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
  maxRegions: {
    type: Number,
    default: 3,
  },
})

const emit = defineEmits(['update:modelValue'])

const sidos = ref([])
const sigungus = ref([])
const dongs = ref([])
const selectedSido = ref('')
const selectedSigungu = ref('')
const selectedDongId = ref('')
const localError = ref('')
const isLoadingSidos = ref(false)
const isLoadingSigungus = ref(false)
const isLoadingDongs = ref(false)

const selectedRegions = computed(() => props.modelValue || [])
const selectedCount = computed(() => selectedRegions.value.length)
const selectedRegionIds = computed(() =>
  selectedRegions.value
    .map((item) => Number(item?.region_id ?? item?.id))
    .filter(Boolean),
)
const canAddMore = computed(() => selectedCount.value < props.maxRegions)
const canMove = computed(() => selectedCount.value > 1)
const selectedDong = computed(() =>
  dongs.value.find((item) => Number(item.id) === Number(selectedDongId.value)) || null,
)

function normalizeRegion(item, priority) {
  const regionId = Number(item?.region_id ?? item?.id)
  return {
    id: item?.id ?? regionId,
    region_id: regionId,
    sido: item?.sido ?? '',
    sigungu: item?.sigungu ?? '',
    dong: item?.dong ?? '',
    priority,
  }
}

function emitRegions(items) {
  emit(
    'update:modelValue',
    items.map((item, index) => normalizeRegion(item, index + 1)),
  )
}

function regionLabel(item) {
  const region = normalizeRegion(item, item?.priority ?? 1)
  return [region.sido, region.sigungu, region.dong].filter(Boolean).join(' ')
}

function regionOptionLabel(item) {
  return [item.sido, item.sigungu, item.dong].filter(Boolean).join(' ')
}

function clearSelectionBelowSido() {
  selectedSigungu.value = ''
  selectedDongId.value = ''
  sigungus.value = []
  dongs.value = []
}

function clearSelectionBelowSigungu() {
  selectedDongId.value = ''
  dongs.value = []
}

async function loadSidos() {
  isLoadingSidos.value = true
  localError.value = ''

  try {
    const data = await getSidos()
    sidos.value = Array.isArray(data.sidos) ? data.sidos : []
  } catch (error) {
    const normalized = normalizeApiError(error)
    localError.value = normalized.message
    sidos.value = []
  } finally {
    isLoadingSidos.value = false
  }
}

async function loadSigungus() {
  if (!selectedSido.value) {
    sigungus.value = []
    return
  }

  isLoadingSigungus.value = true

  try {
    const data = await getSigungus(selectedSido.value)
    sigungus.value = Array.isArray(data.sigungus) ? data.sigungus : []
  } catch (error) {
    const normalized = normalizeApiError(error)
    localError.value = normalized.message
    sigungus.value = []
  } finally {
    isLoadingSigungus.value = false
  }
}

async function loadDongs() {
  if (!selectedSido.value || !selectedSigungu.value) {
    dongs.value = []
    return
  }

  isLoadingDongs.value = true

  try {
    const data = await getDongs(selectedSido.value, selectedSigungu.value)
    dongs.value = Array.isArray(data.regions) ? data.regions : []
  } catch (error) {
    const normalized = normalizeApiError(error)
    localError.value = normalized.message
    dongs.value = []
  } finally {
    isLoadingDongs.value = false
  }
}

async function handleSidoChange() {
  localError.value = ''
  clearSelectionBelowSido()
  await loadSigungus()
}

async function handleSigunguChange() {
  localError.value = ''
  clearSelectionBelowSigungu()
  await loadDongs()
}

function addRegion() {
  localError.value = ''

  if (!selectedDong.value) {
    localError.value = '동/읍/면을 선택해 주세요.'
    return
  }

  if (!canAddMore.value) {
    localError.value = `지역은 최대 ${props.maxRegions}개까지 선택할 수 있습니다.`
    return
  }

  if (selectedRegionIds.value.includes(Number(selectedDong.value.id))) {
    localError.value = '같은 지역은 중복 선택할 수 없습니다.'
    return
  }

  emitRegions([
    ...selectedRegions.value,
    {
      id: selectedDong.value.id,
      region_id: selectedDong.value.id,
      sido: selectedDong.value.sido,
      sigungu: selectedDong.value.sigungu,
      dong: selectedDong.value.dong,
    },
  ])

  selectedDongId.value = ''
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

onMounted(loadSidos)
</script>

<template>
  <section class="form-section region-box">
    <div class="section-heading">
      <h2>나의 지역</h2>
      <span>{{ selectedCount }}/{{ maxRegions }}</span>
    </div>

    <div class="region-selector">
      <div class="region-selector__controls">
        <div class="form-field">
          <label for="region-sido">시도</label>
          <select
            id="region-sido"
            v-model="selectedSido"
            :disabled="isLoadingSidos"
            @change="handleSidoChange"
          >
            <option value="">시도를 선택해 주세요</option>
            <option v-for="sido in sidos" :key="sido" :value="sido">
              {{ sido }}
            </option>
          </select>
        </div>

        <div class="form-field">
          <label for="region-sigungu">시군구</label>
          <select
            id="region-sigungu"
            v-model="selectedSigungu"
            :disabled="!selectedSido || isLoadingSigungus"
            @change="handleSigunguChange"
          >
            <option value="">
              {{ selectedSido ? '시군구를 선택해 주세요' : '먼저 시도를 선택해 주세요' }}
            </option>
            <option v-for="sigungu in sigungus" :key="sigungu" :value="sigungu">
              {{ sigungu }}
            </option>
          </select>
        </div>

        <div class="form-field">
          <label for="region-dong">동/읍/면</label>
          <select
            id="region-dong"
            v-model="selectedDongId"
            :disabled="!selectedSigungu || isLoadingDongs"
          >
            <option value="">
              {{ selectedSigungu ? '동/읍/면을 선택해 주세요' : '먼저 시군구를 선택해 주세요' }}
            </option>
            <option v-for="region in dongs" :key="region.id" :value="String(region.id)">
              {{ regionOptionLabel(region) }}
            </option>
          </select>
        </div>

        <button
          class="button button--secondary region-selector__add"
          type="button"
          :disabled="!selectedDong || !canAddMore"
          @click="addRegion"
        >
          추가
        </button>
      </div>

      <p v-if="selectedSido && !sigungus.length && !isLoadingSigungus" class="muted-text">
        선택한 시도의 시군구 정보가 없습니다.
      </p>

      <p v-if="selectedSigungu && !dongs.length && !isLoadingDongs" class="muted-text">
        선택한 시군구의 동/읍/면 정보가 없습니다.
      </p>
    </div>

    <ul v-if="selectedRegions.length" class="selected-list">
      <li
        v-for="(item, index) in selectedRegions"
        :key="item.region_id ?? item.id"
        class="selected-item"
      >
        <span>{{ index + 1 }}순위 · {{ regionLabel(item) }}</span>
        <span class="button-group">
          <button
            type="button"
            class="mini-button"
            :disabled="!canMove || index === 0"
            @click="moveRegion(index, index - 1)"
          >
            위로
          </button>
          <button
            type="button"
            class="mini-button"
            :disabled="!canMove || index === selectedRegions.length - 1"
            @click="moveRegion(index, index + 1)"
          >
            아래로
          </button>
          <button type="button" class="mini-button" @click="removeRegion(index)">
            삭제
          </button>
        </span>
      </li>
    </ul>

    <p v-if="localError" class="field-error" role="alert">{{ localError }}</p>
    <FormFieldError :errors="errors" />
  </section>
</template>
