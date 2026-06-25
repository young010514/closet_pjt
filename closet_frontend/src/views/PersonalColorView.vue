<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  createPersonalColorAnalysis,
  deletePersonalColorAnalysis,
  getPersonalColorAnalyses,
  normalizePersonalColorError,
} from '@/api/personalColor'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const HISTORY_PAGE_SIZE = 8
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024
const MIN_IMAGE_DIMENSION = 256
const MAX_IMAGE_DIMENSION = 4096

const ALLOWED_IMAGE_MIME_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])
const ALLOWED_IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp'])
const MIME_EXTENSION_MAP = {
  'image/jpeg': new Set(['.jpg', '.jpeg']),
  'image/png': new Set(['.png']),
  'image/webp': new Set(['.webp']),
}

const UPLOAD_ERROR_CODES = new Set([
  'image_required',
  'unsupported_image_type',
  'image_type_mismatch',
  'file_too_large',
  'corrupted_image',
  'invalid_image',
  'image_too_small',
  'image_too_large',
])

const RESULT_THEMES = {
  spring_warm: {
    label: '봄 웜톤',
    accent: '#F49A8A',
    soft: 'rgba(244, 154, 138, 0.16)',
    swatches: ['#F49A8A', '#F6D86B', '#CDE8C8', '#A6D8D4'],
  },
  summer_cool: {
    label: '여름 쿨톤',
    accent: '#8EA4C8',
    soft: 'rgba(142, 164, 200, 0.18)',
    swatches: ['#C8B5F5', '#8EA4C8', '#E6A7B5', '#B8BFC9'],
  },
  autumn_warm: {
    label: '가을 웜톤',
    accent: '#C76A4A',
    soft: 'rgba(199, 106, 74, 0.18)',
    swatches: ['#C76A4A', '#C19A6B', '#6F7B3B', '#D8B58B'],
  },
  winter_cool: {
    label: '겨울 쿨톤',
    accent: '#2D5BFF',
    soft: 'rgba(45, 91, 255, 0.16)',
    swatches: ['#2D5BFF', '#D63B9B', '#FFFFFF', '#2F343F'],
  },
}

const SEASON_PREVIEWS = [
  {
    key: 'spring_warm',
    title: '봄 웜톤',
    description: '밝고 따뜻한 색감',
  },
  {
    key: 'summer_cool',
    title: '여름 쿨톤',
    description: '부드럽고 차분한 색감',
  },
  {
    key: 'autumn_warm',
    title: '가을 웜톤',
    description: '깊고 안정적인 색감',
  },
  {
    key: 'winter_cool',
    title: '겨울 쿨톤',
    description: '선명하고 또렷한 색감',
  },
]

const ANALYSIS_STEPS = [
  '이미지 확인 중',
  '피부 톤 분석 중',
  '어울리는 컬러 구성 중',
]

const METRIC_LABELS = {
  warmth: '웜 성향',
  brightness: '밝기',
  saturation: '채도',
  contrast: '대비감',
}

const fileInputRef = ref(null)
const resultPanelRef = ref(null)
const deleteDialogRef = ref(null)

const selectedFile = ref(null)
const selectedFileMeta = ref(null)
const previewUrl = ref('')
const isDragging = ref(false)
const isAnalyzing = ref(false)
const uploadError = ref('')
const analysisError = ref('')
const analysisFeedback = ref('')
const activeAnalysis = ref(null)
const copiedHex = ref('')
const historyMessage = ref('')
const historyError = ref('')
const historyRecords = ref([])
const historyCount = ref(0)
const historyPage = ref(1)
const historyPageSize = ref(HISTORY_PAGE_SIZE)
const isLoadingHistory = ref(false)
const pendingDeleteAnalysis = ref(null)
const isDeleting = ref(false)
const prefersReducedMotion = ref(false)

let previewObjectUrl = ''
let copyFeedbackTimer = null
let motionMediaQuery = null
let motionListener = null

const activeAnalysisId = computed(() => activeAnalysis.value?.id ?? null)

const activeTheme = computed(() => {
  if (!activeAnalysis.value?.result_type) {
    return RESULT_THEMES.spring_warm
  }

  return RESULT_THEMES[activeAnalysis.value.result_type] ?? RESULT_THEMES.spring_warm
})

const resultPanelStyle = computed(() => ({
  '--analysis-accent': activeTheme.value.accent,
  '--analysis-accent-soft': activeTheme.value.soft,
}))

const historyPageCount = computed(() =>
  Math.max(1, Math.ceil(historyCount.value / Math.max(historyPageSize.value, 1))),
)

const historyPageItems = computed(() =>
  buildPageItems(historyPage.value, historyPageCount.value),
)

const HEX_COLOR_PATTERN = /^#[0-9a-f]{6}$/i

const bestColors = computed(() => normalizeColorList(activeAnalysis.value?.best_colors, 'best'))

const avoidColors = computed(() => normalizeColorList(activeAnalysis.value?.avoid_colors, 'avoid'))
const recommendations = computed(() => {
  const source = activeAnalysis.value?.recommendations || {}

  return {
    clothing: Array.isArray(source.clothing) ? source.clothing : [],
    makeup: Array.isArray(source.makeup) ? source.makeup : [],
    accessories: Array.isArray(source.accessories) ? source.accessories : [],
  }
})

const confidenceValue = computed(() => Number(activeAnalysis.value?.confidence ?? 0))

const confidencePercent = computed(() => Math.round(confidenceValue.value))

const metricItems = computed(() => {
  const source = activeAnalysis.value?.analysis_metrics || {}

  return Object.entries(METRIC_LABELS).map(([key, label]) => {
    const raw = Number(source[key] ?? 0)
    const value = Number.isFinite(raw) ? raw : 0
    return {
      key,
      label,
      percent: Math.round(value * 100),
    }
  })
})

const representativeColor = computed(() => {
  const color = bestColors.value[0]
  return color || null
})

const resultPlaceholderText = computed(() => {
  if (activeAnalysis.value) {
    return '선택한 기록의 상세 결과를 다시 확인할 수 있습니다.'
  }

  if (historyCount.value > 0) {
    return '아래 기록에서 이전 진단을 선택해 확인해 보세요.'
  }

  return '사진을 등록하면 분석 결과가 여기에 표시됩니다.'
})

function buildPageItems(page, pageCount) {
  const total = Math.max(1, pageCount)
  const current = Math.min(Math.max(page, 1), total)

  if (total <= 7) {
    return Array.from({ length: total }, (_, index) => index + 1)
  }

  const items = [1]
  let start = Math.max(2, current - 1)
  let end = Math.min(total - 1, current + 1)

  if (current <= 3) {
    start = 2
    end = 4
  } else if (current >= total - 2) {
    start = total - 3
    end = total - 1
  }

  if (start > 2) {
    items.push('ellipsis-start')
  }

  for (let pageNumber = start; pageNumber <= end; pageNumber += 1) {
    items.push(pageNumber)
  }

  if (end < total - 1) {
    items.push('ellipsis-end')
  }

  items.push(total)
  return items
}

function normalizeMimeType(value) {
  return String(value || '')
    .split(';', 1)[0]
    .trim()
    .toLowerCase()
}

function getFileExtension(name) {
  const index = String(name || '').lastIndexOf('.')
  return index >= 0 ? String(name).slice(index).toLowerCase() : ''
}

function formatBytes(bytes) {
  const size = Number(bytes || 0)
  if (!Number.isFinite(size) || size <= 0) return '0 B'

  const units = ['B', 'KB', 'MB', 'GB']
  let current = size
  let unitIndex = 0

  while (current >= 1024 && unitIndex < units.length - 1) {
    current /= 1024
    unitIndex += 1
  }

  return `${current.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}

function formatDate(value) {
  if (!value) return '-'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'

  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

function formatConfidence(value) {
  return `${Math.round(Number(value || 0))}%`
}

function isSelectedRecord(record) {
  return Number(record?.id) === Number(activeAnalysisId.value)
}

function getRecordTheme(record) {
  return RESULT_THEMES[record?.result_type] ?? RESULT_THEMES.spring_warm
}

function normalizeColorItem(value, index, prefix) {
  if (value === null || value === undefined || value === '') return null

  if (typeof value !== 'object') {
    const name = String(value).trim()
    if (!name) return null

    return {
      id: `${prefix}-${index}-${name}`,
      name,
      hex: '',
      reason: '',
      hasValidHex: false,
    }
  }

  const rawName = value.name ?? value.color ?? value.label ?? ''
  const rawHex = String(value.hex ?? value.code ?? '').trim()
  const hasValidHex = HEX_COLOR_PATTERN.test(rawHex)
  const name = String(rawName || rawHex || `Color ${index + 1}`).trim()
  const reason = String(value.reason ?? value.description ?? '').trim()

  return {
    id: `${prefix}-${index}-${name}-${hasValidHex ? rawHex : 'no-hex'}`,
    name,
    hex: hasValidHex ? rawHex : '',
    reason,
    hasValidHex,
  }
}

function normalizeColorList(value, prefix) {
  if (!Array.isArray(value)) return []

  return value
    .map((item, index) => normalizeColorItem(item, index, prefix))
    .filter(Boolean)
}

function getRepresentativeColor(record) {
  const [color] = normalizeColorList(record?.best_colors, 'history')
  return color || null
}

function getClipboardText(color) {
  return [color?.name, color?.hex].filter(Boolean).join(' ')
}

function updatePreview(file) {
  if (previewObjectUrl) {
    URL.revokeObjectURL(previewObjectUrl)
    previewObjectUrl = ''
  }

  if (!file) {
    previewUrl.value = ''
    return
  }

  previewObjectUrl = URL.createObjectURL(file)
  previewUrl.value = previewObjectUrl
}

function clearFileInput() {
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

function resetUploadState() {
  uploadError.value = ''
  analysisError.value = ''
  analysisFeedback.value = ''
}

function createUploadError(code, message) {
  const error = new Error(message)
  error.code = code
  return error
}

async function readImageDimensions(file) {
  return await new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file)
    const image = new Image()

    image.onload = () => {
      URL.revokeObjectURL(objectUrl)
      resolve({
        width: image.naturalWidth,
        height: image.naturalHeight,
      })
    }

    image.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      reject(createUploadError('corrupted_image', '손상된 이미지 파일입니다.'))
    }

    image.src = objectUrl
  })
}

async function validateSelectedFile(file) {
  if (!file) {
    throw createUploadError('image_required', '이미지 파일을 선택해 주세요.')
  }

  const contentType = normalizeMimeType(file.type)
  const extension = getFileExtension(file.name)

  if (file.size > MAX_UPLOAD_BYTES) {
    throw createUploadError('file_too_large', '파일 크기는 10MB 이하여야 합니다.')
  }

  if (!ALLOWED_IMAGE_MIME_TYPES.has(contentType)) {
    throw createUploadError(
      'unsupported_image_type',
      'JPEG, PNG, WEBP 이미지 파일만 업로드할 수 있습니다.',
    )
  }

  if (!ALLOWED_IMAGE_EXTENSIONS.has(extension)) {
    throw createUploadError(
      'unsupported_image_type',
      'JPEG, PNG, WEBP 이미지 파일만 업로드할 수 있습니다.',
    )
  }

  if (!MIME_EXTENSION_MAP[contentType]?.has(extension)) {
    throw createUploadError(
      'image_type_mismatch',
      '파일 확장자와 MIME 형식이 일치하지 않습니다.',
    )
  }

  const dimensions = await readImageDimensions(file)

  if (
    dimensions.width < MIN_IMAGE_DIMENSION ||
    dimensions.height < MIN_IMAGE_DIMENSION
  ) {
    throw createUploadError(
      'image_too_small',
      '이미지 크기는 최소 256 x 256이어야 합니다.',
    )
  }

  if (
    dimensions.width > MAX_IMAGE_DIMENSION ||
    dimensions.height > MAX_IMAGE_DIMENSION
  ) {
    throw createUploadError(
      'image_too_large',
      '이미지 크기는 최대 4096 x 4096을 초과할 수 없습니다.',
    )
  }

  return {
    dimensions,
    contentType,
    extension,
  }
}

async function applySelectedFile(file) {
  if (!file) return

  try {
    const validated = await validateSelectedFile(file)

    selectedFile.value = file
    selectedFileMeta.value = {
      name: file.name,
      size: file.size,
      type: validated.contentType,
      dimensions: validated.dimensions,
    }

    resetUploadState()
  } catch (error) {
    const normalized = error?.code
      ? {
          code: error.code,
          message: error.message,
        }
      : normalizePersonalColorError(error)

    uploadError.value = normalized.message
  } finally {
    clearFileInput()
  }
}

function openFileDialog() {
  if (isAnalyzing.value) return
  fileInputRef.value?.click()
}

function handleFileChange(event) {
  const [file] = Array.from(event.target.files || [])
  void applySelectedFile(file)
}

function handleDragOver() {
  if (isAnalyzing.value) return
  isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}

function handleDrop(event) {
  if (isAnalyzing.value) return

  isDragging.value = false
  const [file] = Array.from(event.dataTransfer?.files || [])
  void applySelectedFile(file)
}

function clearSelectedFile() {
  selectedFile.value = null
  selectedFileMeta.value = null
  updatePreview(null)
  clearFileInput()
  resetUploadState()
}

function replaceSelectedFile() {
  openFileDialog()
}

function handleSessionExpired() {
  authStore.user = null
  router.push({
    name: 'login',
    query: { redirect: route.fullPath },
  })
}

async function scrollToResultPanel() {
  await nextTick()

  if (!resultPanelRef.value) return

  resultPanelRef.value.scrollIntoView({
    behavior: prefersReducedMotion.value ? 'auto' : 'smooth',
    block: 'start',
  })
}

async function loadHistoryPage(page = 1, { selectFirst = false } = {}) {
  isLoadingHistory.value = true
  historyError.value = ''
  historyMessage.value = ''

  try {
    const data = await getPersonalColorAnalyses({
      page,
      page_size: HISTORY_PAGE_SIZE,
    })

    const records = Array.isArray(data.results) ? data.results : []

    historyRecords.value = records
    historyCount.value = Number(data.count ?? 0)
    historyPage.value = Number(data.page ?? page) || page
    historyPageSize.value = Number(data.page_size ?? HISTORY_PAGE_SIZE) || HISTORY_PAGE_SIZE

    if (activeAnalysis.value) {
      const refreshed = records.find((record) => Number(record.id) === Number(activeAnalysis.value.id))
      if (refreshed) {
        activeAnalysis.value = refreshed
      }
    } else if (selectFirst && records.length > 0) {
      activeAnalysis.value = records[0]
    }
  } catch (error) {
    const normalized = normalizePersonalColorError(error)
    if ([401, 403].includes(normalized.status)) {
      handleSessionExpired()
      return
    }
    historyError.value = normalized.message
  } finally {
    isLoadingHistory.value = false
  }
}

async function refreshHistory({ selectFirst = false } = {}) {
  await loadHistoryPage(historyPage.value, { selectFirst })
}

async function selectHistoryRecord(record, { scroll = true } = {}) {
  activeAnalysis.value = record
  analysisFeedback.value = ''
  analysisError.value = ''
  uploadError.value = ''

  if (scroll) {
    await scrollToResultPanel()
  }
}

async function startAnalysis() {
  if (isAnalyzing.value) return

  if (!selectedFile.value) {
    uploadError.value = '이미지 파일을 선택해 주세요.'
    return
  }

  isAnalyzing.value = true
  uploadError.value = ''
  analysisError.value = ''
  analysisFeedback.value = ''
  historyMessage.value = ''

  try {
    const result = await createPersonalColorAnalysis(selectedFile.value)
    activeAnalysis.value = result
    analysisFeedback.value = '분석 결과가 저장되었습니다.'
    await loadHistoryPage(1, { selectFirst: false })
    await scrollToResultPanel()
  } catch (error) {
    const normalized = normalizePersonalColorError(error)

    if ([401, 403].includes(normalized.status)) {
      handleSessionExpired()
      return
    }

    if (UPLOAD_ERROR_CODES.has(normalized.code)) {
      uploadError.value = normalized.message
    } else {
      analysisError.value = normalized.message
    }
  } finally {
    isAnalyzing.value = false
  }
}

function goToHistoryPage(page) {
  if (page < 1 || page > historyPageCount.value || page === historyPage.value) return
  void loadHistoryPage(page, { selectFirst: true })
}

function openDeleteDialog(record) {
  if (isDeleting.value) return
  pendingDeleteAnalysis.value = record
  if (deleteDialogRef.value && !deleteDialogRef.value.open) {
    deleteDialogRef.value.showModal()
  }
}

function closeDeleteDialog() {
  if (deleteDialogRef.value?.open) {
    deleteDialogRef.value.close()
  }
}

function handleDeleteDialogClose() {
  pendingDeleteAnalysis.value = null
}

async function confirmDelete() {
  if (!pendingDeleteAnalysis.value || isDeleting.value) return

  isDeleting.value = true
  historyError.value = ''

  const deletingRecord = pendingDeleteAnalysis.value

  try {
    await deletePersonalColorAnalysis(deletingRecord.id)

    if (Number(activeAnalysis.value?.id) === Number(deletingRecord.id)) {
      activeAnalysis.value = null
    }

    const nextPage =
      historyRecords.value.length === 1 && historyPage.value > 1
        ? historyPage.value - 1
        : historyPage.value

    closeDeleteDialog()
    await loadHistoryPage(nextPage, { selectFirst: false })
    historyMessage.value = '기록을 삭제했습니다.'
  } catch (error) {
    const normalized = normalizePersonalColorError(error)
    if ([401, 403].includes(normalized.status)) {
      handleSessionExpired()
      return
    }
    historyError.value = normalized.message
  } finally {
    isDeleting.value = false
  }
}

async function copyHexCode(color) {
  if (!color?.hex) return

  try {
    await navigator.clipboard.writeText(color.hex)
    copiedHex.value = color.hex
    if (copyFeedbackTimer) {
      clearTimeout(copyFeedbackTimer)
    }
    copyFeedbackTimer = window.setTimeout(() => {
      copiedHex.value = ''
      copyFeedbackTimer = null
    }, 1500)
  } catch {
    copiedHex.value = ''
  }
}

function formatMetricValue(value) {
  return `${value}%`
}

watch(selectedFile, (file) => {
  updatePreview(file)
})

watch(
  () => route.fullPath,
  () => {
    historyMessage.value = ''
  },
)

onMounted(() => {
  void loadHistoryPage(1, { selectFirst: true })

  if (window.matchMedia) {
    motionMediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    prefersReducedMotion.value = motionMediaQuery.matches
    motionListener = (event) => {
      prefersReducedMotion.value = event.matches
    }
    if (typeof motionMediaQuery.addEventListener === 'function') {
      motionMediaQuery.addEventListener('change', motionListener)
    } else if (typeof motionMediaQuery.addListener === 'function') {
      motionMediaQuery.addListener(motionListener)
    }
  }
})

onBeforeUnmount(() => {
  if (previewObjectUrl) {
    URL.revokeObjectURL(previewObjectUrl)
    previewObjectUrl = ''
  }

  if (copyFeedbackTimer) {
    clearTimeout(copyFeedbackTimer)
    copyFeedbackTimer = null
  }

  if (motionMediaQuery && motionListener) {
    if (typeof motionMediaQuery.removeEventListener === 'function') {
      motionMediaQuery.removeEventListener('change', motionListener)
    } else if (typeof motionMediaQuery.removeListener === 'function') {
      motionMediaQuery.removeListener(motionListener)
    }
  }
})
</script>

<template>
  <main class="page-view personal-color-view">
    <section class="panel personal-color-hero">
      <p class="eyebrow">AI COLOR ANALYSIS</p>
      <h1>나에게 어울리는 컬러를 찾아보세요</h1>
      <p class="lead-text">
        사진 한 장으로 피부 톤과 대비감을 분석해 어울리는 컬러와 스타일을 추천합니다.
      </p>
      <p class="personal-color-hero__note">
        조명, 카메라 색감, 메이크업 상태에 따라 결과가 달라질 수 있으며 본 진단은 참고용입니다.
      </p>
    </section>

    <section class="personal-color-grid">
      <section class="panel upload-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Upload</p>
            <h2>사진 업로드</h2>
          </div>
          <span class="muted-text">JPEG, PNG, WEBP · 최대 10MB</span>
        </div>

        <p v-if="uploadError" id="personal-color-upload-error" class="alert alert--error" role="alert">
          {{ uploadError }}
        </p>

        <label
          class="upload-dropzone"
          :class="{ 'upload-dropzone--dragging': isDragging, 'upload-dropzone--has-file': selectedFile }"
          for="personal-color-image-input"
          tabindex="0"
          role="button"
          :aria-invalid="Boolean(uploadError)"
          aria-describedby="personal-color-upload-help personal-color-upload-error"
          @dragenter.prevent="handleDragOver"
          @dragover.prevent="handleDragOver"
          @dragleave.prevent="handleDragLeave"
          @drop.prevent="handleDrop"
          @keydown.enter.prevent="openFileDialog"
          @keydown.space.prevent="openFileDialog"
        >
          <input
            id="personal-color-image-input"
            ref="fileInputRef"
            class="sr-only"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            @change="handleFileChange"
          />

          <div v-if="!selectedFile" class="upload-dropzone__empty">
            <div class="upload-dropzone__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" role="presentation">
                <path
                  d="M7 17h10a4 4 0 0 0 .6-7.95A5.5 5.5 0 0 0 7.28 7.9 3.75 3.75 0 0 0 7 17Zm5-9v6m0-6-2 2m2-2 2 2"
                  fill="none"
                  stroke="currentColor"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="1.6"
                />
              </svg>
            </div>
            <strong>이미지를 드래그하거나 클릭해 선택</strong>
            <span id="personal-color-upload-help">한 장의 얼굴 사진만 업로드해 주세요.</span>
          </div>

          <div v-else class="upload-preview">
            <img
              :src="previewUrl"
              :alt="selectedFile?.name ? `${selectedFile.name} 미리보기` : '선택한 이미지 미리보기'"
            />
            <div class="upload-preview__meta">
              <strong>{{ selectedFile.name }}</strong>
              <p>{{ formatBytes(selectedFile.size) }}</p>
              <p v-if="selectedFileMeta?.dimensions">
                {{ selectedFileMeta.dimensions.width }} x {{ selectedFileMeta.dimensions.height }}
              </p>
            </div>
          </div>
        </label>

        <div class="upload-actions">
          <button
            class="button button--secondary"
            type="button"
            :disabled="!selectedFile || isAnalyzing"
            @click="replaceSelectedFile"
          >
            이미지 교체
          </button>
          <button
            class="button button--secondary"
            type="button"
            :disabled="!selectedFile || isAnalyzing"
            @click="clearSelectedFile"
          >
            이미지 제거
          </button>
          <button
            class="button button--primary upload-actions__cta"
            type="button"
            :disabled="!selectedFile || isAnalyzing"
            @click="startAnalysis"
          >
            {{ isAnalyzing ? '분석 중' : 'AI로 분석하기' }}
          </button>
        </div>

        <p v-if="analysisError" class="status-text status-text--error" role="alert">
          {{ analysisError }}
        </p>

        <ol class="upload-guides">
          <li>자연광에서 촬영해 주세요</li>
          <li>필터와 진한 메이크업은 피해주세요</li>
          <li>얼굴이 정면 중앙에 오도록 촬영해 주세요</li>
        </ol>

        <p class="upload-privacy">
          원본 사진은 진단 기록에 저장하지 않으며 분석 완료 후 폐기됩니다.
        </p>
      </section>

      <section
        ref="resultPanelRef"
        class="panel result-panel"
        :style="resultPanelStyle"
        aria-live="polite"
      >
        <div class="section-heading">
          <div>
            <p class="eyebrow">Result</p>
            <h2>분석 결과</h2>
          </div>
          <span v-if="activeAnalysis" class="result-panel__updated">
            {{ formatDate(activeAnalysis.created_at) }}
          </span>
        </div>

        <p v-if="analysisFeedback" class="status-text" role="status">{{ analysisFeedback }}</p>

        <div v-if="isAnalyzing" class="analysis-loading" role="status">
          <div class="analysis-loading__header">
            <strong>AI가 사진을 분석하고 있습니다.</strong>
            <span class="muted-text">잠시만 기다려 주세요.</span>
          </div>
          <ol class="analysis-steps">
            <li v-for="step in ANALYSIS_STEPS" :key="step">
              <span class="analysis-steps__dot" aria-hidden="true"></span>
              <span>{{ step }}</span>
            </li>
          </ol>
        </div>

        <template v-else-if="activeAnalysis">
          <div class="result-hero">
            <div class="result-badges">
              <span class="result-badge">{{ activeAnalysis.result_label }}</span>
              <span v-if="activeAnalysis.result_subtype" class="result-badge result-badge--ghost">
                {{ activeAnalysis.result_subtype }}
              </span>
            </div>

            <div class="confidence-meter">
              <div class="confidence-meter__header">
                <span>신뢰도</span>
                <strong>{{ formatConfidence(activeAnalysis.confidence) }}</strong>
              </div>
              <div
                class="confidence-meter__bar"
                role="meter"
                aria-label="신뢰도"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-valuenow="confidencePercent"
                :aria-valuetext="formatConfidence(activeAnalysis.confidence)"
              >
                <span :style="{ width: `${confidencePercent}%` }"></span>
              </div>
            </div>
          </div>

          <div class="result-strip" aria-hidden="true">
            <span
              v-for="(swatch, index) in activeTheme.swatches"
              :key="`${activeAnalysis.result_type}-${index}`"
              :style="{ backgroundColor: swatch }"
            />
          </div>

          <p class="result-summary">
            {{ activeAnalysis.summary }}
          </p>

          <section class="metric-grid" aria-label="세부 분석 지표">
            <article v-for="metric in metricItems" :key="metric.key" class="metric-card">
              <div class="metric-card__header">
                <span>{{ metric.label }}</span>
                <strong>{{ formatMetricValue(metric.percent) }}</strong>
              </div>
              <div
                class="metric-card__bar"
                role="meter"
                :aria-label="metric.label"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-valuenow="metric.percent"
              >
                <span :style="{ width: `${metric.percent}%` }"></span>
              </div>
            </article>
          </section>

          <div class="palette-grid">
            <section class="palette-section">
              <div class="section-heading section-heading--compact">
                <h3>추천 색상</h3>
                <span class="muted-text">잘 어울리는 색</span>
              </div>
              <div class="color-list">
                <article
                  v-for="color in bestColors"
                  :key="color.id"
                  class="color-card color-card--positive"
                >
                  <div
                    class="color-card__swatch"
                    :style="{ backgroundColor: color.hasValidHex ? color.hex : 'var(--color-surface-muted)' }"
                    aria-hidden="true"
                  />
                  <div class="color-card__body">
                    <div class="color-card__topline">
                      <strong>{{ color.name }}</strong>
                      <span v-if="color.hasValidHex">{{ color.hex }}</span>
                    </div>
                    <p v-if="color.reason">{{ color.reason }}</p>
                    <button
                      v-if="color.hasValidHex"
                      type="button"
                      class="mini-button color-card__copy"
                      :aria-label="`${color.name} HEX 코드 복사`"
                      @click="copyHexCode(color)"
                    >
                      {{ copiedHex === color.hex ? '복사됨' : 'HEX 복사' }}
                    </button>
                  </div>
                </article>
              </div>
            </section>

            <section class="palette-section">
              <div class="section-heading section-heading--compact">
                <h3>피하면 좋은 색상</h3>
                <span class="muted-text">주의할 색</span>
              </div>
              <div class="color-list">
                <article
                  v-for="color in avoidColors"
                  :key="color.id"
                  class="color-card color-card--negative"
                >
                  <div
                    class="color-card__swatch"
                    :style="{ backgroundColor: color.hasValidHex ? color.hex : 'var(--color-surface-muted)' }"
                    aria-hidden="true"
                  />
                  <div class="color-card__body">
                    <div class="color-card__topline">
                      <strong>{{ color.name }}</strong>
                      <span v-if="color.hasValidHex">{{ color.hex }}</span>
                    </div>
                    <p v-if="color.reason">{{ color.reason }}</p>
                    <button
                      v-if="color.hasValidHex"
                      type="button"
                      class="mini-button color-card__copy"
                      :aria-label="`${color.name} HEX 코드 복사`"
                      @click="copyHexCode(color)"
                    >
                      {{ copiedHex === color.hex ? '복사됨' : 'HEX 복사' }}
                    </button>
                  </div>
                </article>
              </div>
            </section>
          </div>

          <div class="recommendation-grid">
            <section class="recommendation-card">
              <div class="section-heading section-heading--compact">
                <h3>의류 추천</h3>
              </div>
              <ul>
                <li v-for="item in recommendations.clothing" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="recommendation-card">
              <div class="section-heading section-heading--compact">
                <h3>메이크업 추천</h3>
              </div>
              <ul>
                <li v-for="item in recommendations.makeup" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="recommendation-card">
              <div class="section-heading section-heading--compact">
                <h3>액세서리 추천</h3>
              </div>
              <ul>
                <li v-for="item in recommendations.accessories" :key="item">{{ item }}</li>
              </ul>
            </section>
          </div>

          <div class="result-actions">
            <button class="button button--primary" type="button" @click="openFileDialog">
              다시 분석하기
            </button>
          </div>
        </template>

        <template v-else>
          <div class="result-empty">
            <div class="season-preview-grid" aria-hidden="true">
              <article
                v-for="season in SEASON_PREVIEWS"
                :key="season.key"
                class="season-preview-card"
              >
                <div class="season-preview-card__swatches">
                  <span
                    v-for="(swatch, index) in RESULT_THEMES[season.key].swatches"
                    :key="`${season.key}-${index}`"
                    :style="{ backgroundColor: swatch }"
                  />
                </div>
                <strong>{{ season.title }}</strong>
                <span>{{ season.description }}</span>
              </article>
            </div>
            <p class="result-empty__message">{{ resultPlaceholderText }}</p>
          </div>
        </template>
      </section>
    </section>

    <section class="panel history-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">History</p>
          <h2>나의 진단 기록</h2>
        </div>
        <span class="muted-text">총 {{ historyCount.toLocaleString('ko-KR') }}건</span>
      </div>

      <p v-if="historyMessage" class="status-text" role="status">{{ historyMessage }}</p>

      <p v-if="historyError" class="alert alert--error" role="alert">
        {{ historyError }}
        <button class="mini-button history-retry" type="button" @click="refreshHistory">
          다시 시도
        </button>
      </p>

      <div v-if="isLoadingHistory" class="history-loading" aria-live="polite">
        <div v-for="index in 3" :key="index" class="history-loading__row">
          <span class="history-loading__bar history-loading__bar--small" />
          <span class="history-loading__bar" />
          <span class="history-loading__bar history-loading__bar--wide" />
        </div>
      </div>

      <div v-else-if="!historyError && historyRecords.length === 0" class="history-empty">
        <p>아직 저장된 퍼스널컬러 진단 기록이 없습니다.</p>
        <p>사진을 등록해 첫 번째 진단을 시작해 보세요.</p>
      </div>

      <template v-else>
        <div class="history-table-wrap">
          <table class="history-table">
            <thead>
              <tr>
                <th scope="col">진단일</th>
                <th scope="col">진단 결과</th>
                <th scope="col">세부 타입</th>
                <th scope="col">신뢰도</th>
                <th scope="col">대표 추천 색상</th>
                <th scope="col">상세 보기</th>
                <th scope="col">삭제</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="record in historyRecords"
                :key="record.id"
                :class="{ 'history-table__row--selected': isSelectedRecord(record) }"
                role="button"
                tabindex="0"
                :aria-pressed="isSelectedRecord(record)"
                @click="selectHistoryRecord(record)"
                @keydown.enter.prevent="selectHistoryRecord(record)"
                @keydown.space.prevent="selectHistoryRecord(record)"
              >
                <td>{{ formatDate(record.created_at) }}</td>
                <td>
                  <span class="history-result-badge" :style="{ '--history-accent': getRecordTheme(record).accent }">
                    {{ record.result_label }}
                  </span>
                </td>
                <td>{{ record.result_subtype || '-' }}</td>
                <td>{{ formatConfidence(record.confidence) }}</td>
                <td>
                  <div v-if="getRepresentativeColor(record)" class="history-color">
                    <span
                      class="history-color__swatch"
                      :style="{ backgroundColor: getRepresentativeColor(record).hex }"
                      aria-hidden="true"
                    />
                    <div class="history-color__body">
                      <strong>{{ getRepresentativeColor(record).name }}</strong>
                      <span>{{ getRepresentativeColor(record).hex }}</span>
                    </div>
                  </div>
                  <span v-else>-</span>
                </td>
                <td>
                  <button
                    class="button button--secondary history-action"
                    type="button"
                    @click.stop="selectHistoryRecord(record)"
                  >
                    상세 보기
                  </button>
                </td>
                <td>
                  <button
                    class="button button--secondary history-action history-action--danger"
                    type="button"
                    :disabled="isDeleting"
                    @click.stop="openDeleteDialog(record)"
                  >
                    삭제
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="history-card-list">
          <article
            v-for="record in historyRecords"
            :key="`mobile-${record.id}`"
            class="history-card"
            :class="{ 'history-card--selected': isSelectedRecord(record) }"
            role="button"
            tabindex="0"
            :aria-pressed="isSelectedRecord(record)"
            @click="selectHistoryRecord(record)"
            @keydown.enter.prevent="selectHistoryRecord(record)"
            @keydown.space.prevent="selectHistoryRecord(record)"
          >
            <div class="history-card__header">
              <div>
                <span class="history-card__date">{{ formatDate(record.created_at) }}</span>
                <h3>{{ record.result_label }}</h3>
              </div>
              <span
                class="history-result-badge"
                :style="{ '--history-accent': getRecordTheme(record).accent }"
              >
                {{ formatConfidence(record.confidence) }}
              </span>
            </div>

            <p class="history-card__subtype">{{ record.result_subtype || '-' }}</p>

            <div v-if="getRepresentativeColor(record)" class="history-color history-color--mobile">
              <span
                class="history-color__swatch"
                :style="{ backgroundColor: getRepresentativeColor(record).hex }"
                aria-hidden="true"
              />
              <div class="history-color__body">
                <strong>{{ getRepresentativeColor(record).name }}</strong>
                <span>{{ getRepresentativeColor(record).hex }}</span>
              </div>
            </div>

            <div class="history-card__actions">
              <button
                class="button button--secondary history-action"
                type="button"
                @click.stop="selectHistoryRecord(record)"
              >
                상세 보기
              </button>
              <button
                class="button button--secondary history-action history-action--danger"
                type="button"
                :disabled="isDeleting"
                @click.stop="openDeleteDialog(record)"
              >
                삭제
              </button>
            </div>
          </article>
        </div>

        <nav
          v-if="historyPageCount > 1"
          class="history-pagination"
          aria-label="퍼스널컬러 기록 페이지 이동"
        >
          <button
            type="button"
            class="mini-button"
            :disabled="historyPage <= 1 || isLoadingHistory"
            @click="goToHistoryPage(historyPage - 1)"
          >
            이전
          </button>

          <div class="history-pagination__pages" aria-label="페이지 번호">
            <template v-for="item in historyPageItems" :key="item">
              <button
                v-if="typeof item === 'number'"
                type="button"
                :class="['mini-button', { 'mini-button--active': item === historyPage }]"
                :disabled="isLoadingHistory || item === historyPage"
                @click="goToHistoryPage(item)"
              >
                {{ item }}
              </button>
              <span v-else class="history-pagination__ellipsis">…</span>
            </template>
          </div>

          <button
            type="button"
            class="mini-button"
            :disabled="historyPage >= historyPageCount || isLoadingHistory"
            @click="goToHistoryPage(historyPage + 1)"
          >
            다음
          </button>
        </nav>
      </template>
    </section>

    <dialog
      ref="deleteDialogRef"
      class="delete-dialog"
      @close="handleDeleteDialogClose"
      @cancel.prevent="closeDeleteDialog"
    >
      <div class="delete-dialog__body">
        <p class="eyebrow">Delete</p>
        <h3>진단 기록을 삭제할까요?</h3>
        <p>
          {{ pendingDeleteAnalysis?.result_label || '선택한 기록' }} 기록을 삭제합니다.
          삭제 후에는 다시 복구할 수 없습니다.
        </p>

        <div class="delete-dialog__actions">
          <button type="button" class="button button--secondary" @click="closeDeleteDialog">
            취소
          </button>
          <button
            type="button"
            class="button button--primary"
            :disabled="isDeleting"
            @click="confirmDelete"
          >
            {{ isDeleting ? '삭제 중' : '삭제' }}
          </button>
        </div>
      </div>
    </dialog>
  </main>
</template>

<style scoped>
.personal-color-view {
  display: grid;
  gap: 1rem;
}

.personal-color-hero {
  display: grid;
  gap: 0.45rem;
  background:
    radial-gradient(circle at top right, rgba(47, 125, 109, 0.12), transparent 34%),
    linear-gradient(135deg, rgba(47, 125, 109, 0.08), rgba(255, 255, 255, 0.96));
}

.personal-color-hero__note {
  color: var(--color-text-muted);
  max-width: 64ch;
}

.personal-color-grid {
  display: grid;
  gap: 1rem;
}

.upload-panel,
.result-panel,
.history-panel {
  min-width: 0;
}

.upload-panel,
.result-panel {
  display: grid;
  gap: 1rem;
}

.upload-dropzone {
  display: grid;
  min-height: 280px;
  padding: 1.25rem;
  color: var(--color-text);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(244, 247, 246, 0.96)),
    #fff;
  border: 1px dashed var(--color-border-strong);
  border-radius: 18px;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease,
    transform 0.15s ease,
    box-shadow 0.15s ease;
}

.upload-dropzone:hover,
.upload-dropzone:focus-visible {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(47, 125, 109, 0.14);
  outline: none;
}

.upload-dropzone--dragging {
  background:
    linear-gradient(180deg, rgba(228, 241, 238, 0.92), rgba(255, 255, 255, 0.98)),
    #fff;
  border-color: var(--color-accent);
}

.upload-dropzone--has-file {
  border-style: solid;
}

.upload-dropzone__empty {
  display: grid;
  gap: 0.65rem;
  place-content: center;
  justify-items: center;
  text-align: center;
}

.upload-dropzone__icon {
  display: grid;
  place-items: center;
  width: 72px;
  height: 72px;
  color: var(--color-accent-dark);
  background: var(--color-accent-soft);
  border-radius: 24px;
}

.upload-dropzone__icon svg {
  width: 34px;
  height: 34px;
}

.upload-preview {
  display: grid;
  gap: 0.85rem;
  align-content: start;
}

.upload-preview img {
  width: 100%;
  max-height: 360px;
  object-fit: cover;
  border-radius: 14px;
  border: 1px solid var(--color-border);
}

.upload-preview__meta {
  display: grid;
  gap: 0.2rem;
  color: var(--color-text-muted);
}

.upload-preview__meta strong {
  color: var(--color-heading);
  word-break: break-word;
}

.upload-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.upload-actions__cta {
  grid-column: 1 / -1;
}

.upload-guides {
  display: grid;
  gap: 0.45rem;
  padding-left: 1.2rem;
  color: var(--color-text);
}

.upload-privacy {
  padding: 0.85rem 0.95rem;
  color: var(--color-text-muted);
  background: var(--color-surface-muted);
  border-radius: 12px;
}

.result-panel {
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.96)),
    #fff;
}

.result-panel::before {
  content: '';
  position: absolute;
  inset: 0 auto auto 0;
  width: 100%;
  height: 5px;
  background: var(--analysis-accent);
}

.result-panel__updated {
  color: var(--color-text-muted);
  font-size: 0.82rem;
  font-weight: 700;
}

.analysis-loading {
  display: grid;
  gap: 1rem;
  padding: 1rem 0 0.2rem;
}

.analysis-loading__header {
  display: grid;
  gap: 0.2rem;
}

.analysis-steps {
  display: grid;
  gap: 0.65rem;
  padding: 0;
  list-style: none;
}

.analysis-steps li {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-height: 44px;
  padding: 0.7rem 0.9rem;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: 14px;
}

.analysis-steps__dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--analysis-accent);
  box-shadow: 0 0 0 0 rgba(47, 125, 109, 0.35);
  animation: pulse-dot 1.2s ease-in-out infinite;
}

.result-hero {
  display: grid;
  gap: 0.9rem;
}

.result-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.result-badge {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0.25rem 0.7rem;
  color: var(--color-heading);
  background: var(--analysis-accent-soft);
  border: 1px solid var(--analysis-accent);
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 800;
}

.result-badge--ghost {
  color: var(--color-text);
  background: #fff;
  border-color: var(--color-border-strong);
}

.confidence-meter {
  display: grid;
  gap: 0.4rem;
}

.confidence-meter__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  color: var(--color-heading);
  font-weight: 800;
}

.confidence-meter__bar,
.metric-card__bar {
  position: relative;
  width: 100%;
  height: 12px;
  background: var(--color-surface-muted);
  border-radius: 999px;
  overflow: hidden;
}

.confidence-meter__bar span,
.metric-card__bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--analysis-accent);
}

.result-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.35rem;
}

.result-strip span {
  display: block;
  height: 10px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.result-summary {
  color: var(--color-text);
  font-size: 1rem;
  line-height: 1.7;
}

.metric-grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.metric-card {
  display: grid;
  gap: 0.45rem;
  padding: 0.9rem 1rem;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: 14px;
}

.metric-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.metric-card__header strong {
  color: var(--color-heading);
}

.palette-grid,
.recommendation-grid {
  display: grid;
  gap: 1rem;
}

.palette-section,
.recommendation-card {
  min-width: 0;
}

.palette-section {
  display: grid;
  gap: 0.75rem;
}

.color-list {
  display: grid;
  gap: 0.75rem;
}

.color-card {
  display: grid;
  grid-template-columns: 80px minmax(0, 1fr);
  gap: 0.9rem;
  align-items: stretch;
  padding: 0.9rem;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  box-shadow: var(--shadow-panel);
}

.color-card__swatch {
  min-height: 100px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.color-card__body {
  display: grid;
  gap: 0.55rem;
  min-width: 0;
}

.color-card__topline {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.color-card__topline strong {
  color: var(--color-heading);
  font-size: 1rem;
}

.color-card__topline span {
  color: var(--color-text-muted);
  font-size: 0.82rem;
  font-weight: 700;
  word-break: break-all;
}

.color-card__body p {
  color: var(--color-text);
  line-height: 1.6;
}

.color-card__copy {
  justify-self: start;
}

.color-card--positive {
  border-color: rgba(47, 125, 109, 0.2);
}

.color-card--negative {
  border-color: rgba(180, 35, 24, 0.18);
}

.recommendation-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.recommendation-card {
  display: grid;
  gap: 0.75rem;
  padding: 0.95rem 1rem;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: 14px;
}

.recommendation-card ul {
  display: grid;
  gap: 0.45rem;
  padding-left: 1.2rem;
}

.recommendation-card li {
  color: var(--color-text);
}

.result-actions {
  display: flex;
  justify-content: flex-start;
}

.result-empty {
  display: grid;
  gap: 1rem;
  padding: 0.5rem 0 0.2rem;
}

.season-preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.season-preview-card {
  display: grid;
  gap: 0.55rem;
  padding: 0.95rem;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: 14px;
}

.season-preview-card__swatches {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.35rem;
}

.season-preview-card__swatches span {
  display: block;
  height: 12px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.season-preview-card strong {
  color: var(--color-heading);
}

.season-preview-card span {
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.result-empty__message {
  color: var(--color-text-muted);
  line-height: 1.7;
}

.history-panel {
  display: grid;
  gap: 0.9rem;
}

.history-loading {
  display: grid;
  gap: 0.75rem;
}

.history-loading__row {
  display: grid;
  grid-template-columns: 120px 1.2fr 1fr;
  gap: 0.75rem;
  padding: 0.9rem 1rem;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: 14px;
}

.history-loading__bar {
  display: block;
  min-height: 16px;
  background: linear-gradient(90deg, #e6ecea, #f7f9f8, #e6ecea);
  background-size: 200% 100%;
  border-radius: 999px;
  animation: shimmer 1.4s ease-in-out infinite;
}

.history-loading__bar--small {
  width: 80px;
}

.history-loading__bar--wide {
  width: 70%;
}

.history-empty {
  display: grid;
  gap: 0.35rem;
  padding: 1.2rem;
  color: var(--color-text-muted);
  text-align: center;
  background: var(--color-surface-muted);
  border: 1px dashed var(--color-border-strong);
  border-radius: 14px;
}

.history-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: #fff;
  box-shadow: var(--shadow-panel);
}

.history-table {
  width: 100%;
  border-collapse: collapse;
}

.history-table th,
.history-table td {
  padding: 0.9rem 1rem;
  text-align: left;
  vertical-align: middle;
  border-bottom: 1px solid var(--color-border);
}

.history-table th {
  color: var(--color-heading);
  font-size: 0.85rem;
  font-weight: 800;
  background: var(--color-surface-muted);
  white-space: nowrap;
}

.history-table tbody tr {
  transition: background-color 0.15s ease, box-shadow 0.15s ease;
}

.history-table tbody tr:hover {
  background: rgba(47, 125, 109, 0.06);
}

.history-table tbody tr:focus-visible {
  outline: none;
  background: rgba(47, 125, 109, 0.08);
  box-shadow: inset 0 0 0 2px rgba(47, 125, 109, 0.18);
}

.history-table__row--selected {
  background: rgba(47, 125, 109, 0.08);
}

.history-result-badge {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0.18rem 0.65rem;
  color: var(--color-heading);
  background: rgba(47, 125, 109, 0.08);
  border: 1px solid var(--history-accent, var(--color-accent));
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 800;
}

.history-color {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-width: 0;
}

.history-color--mobile {
  align-items: flex-start;
}

.history-color__swatch {
  flex: none;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.history-color__body {
  display: grid;
  gap: 0.1rem;
  min-width: 0;
}

.history-color__body strong {
  color: var(--color-heading);
}

.history-color__body span {
  color: var(--color-text-muted);
  font-size: 0.82rem;
  word-break: break-all;
}

.history-action {
  min-width: 96px;
}

.history-action--danger {
  color: var(--color-danger);
}

.history-card-list {
  display: none;
  gap: 0.75rem;
}

.history-card {
  display: grid;
  gap: 0.75rem;
  padding: 1rem;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow: var(--shadow-panel);
}

.history-card--selected {
  border-color: var(--color-accent);
  box-shadow: 0 16px 30px rgba(47, 125, 109, 0.16);
}

.history-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.history-card__header h3 {
  margin: 0.15rem 0 0;
  color: var(--color-heading);
  font-size: 1rem;
}

.history-card__date {
  color: var(--color-text-muted);
  font-size: 0.82rem;
  font-weight: 700;
}

.history-card__subtype {
  color: var(--color-text);
  font-weight: 700;
}

.history-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.history-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.history-pagination__pages {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: wrap;
  justify-content: center;
}

.history-pagination__ellipsis {
  color: var(--color-text-muted);
  font-weight: 800;
}

.history-retry {
  margin-left: 0.5rem;
}

.delete-dialog {
  width: min(100%, 480px);
  padding: 0;
  border: 0;
  border-radius: 18px;
  box-shadow: var(--shadow-panel);
}

.delete-dialog::backdrop {
  background: rgba(15, 23, 42, 0.45);
}

.delete-dialog__body {
  display: grid;
  gap: 0.9rem;
  padding: 1.5rem;
  background: #fff;
}

.delete-dialog__body h3 {
  color: var(--color-heading);
  font-size: 1.2rem;
}

.delete-dialog__body p {
  color: var(--color-text);
  line-height: 1.6;
}

.delete-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 0.2rem;
}

@keyframes pulse-dot {
  0%,
  100% {
    transform: scale(1);
    opacity: 0.7;
  }

  50% {
    transform: scale(1.1);
    opacity: 1;
  }
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }

  100% {
    background-position: -200% 0;
  }
}

@media (min-width: 960px) {
  .personal-color-grid {
    grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
    align-items: start;
  }

  .palette-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 720px) {
  .recommendation-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .upload-actions,
  .metric-grid,
  .season-preview-grid {
    grid-template-columns: 1fr;
  }

  .palette-grid {
    grid-template-columns: 1fr;
  }

  .recommendation-grid {
    grid-template-columns: 1fr;
  }

  .history-table-wrap {
    display: none;
  }

  .history-card-list {
    display: grid;
  }

  .history-card__header,
  .delete-dialog__actions,
  .history-pagination {
    align-items: flex-start;
    flex-direction: column;
  }

  .history-card__actions {
    flex-direction: column;
  }

  .history-action,
  .history-action--danger,
  .history-retry {
    width: 100%;
  }

  .history-pagination__pages {
    width: 100%;
    justify-content: flex-start;
  }

  .color-card {
    grid-template-columns: 1fr;
  }

  .color-card__swatch {
    min-height: 84px;
  }

  .upload-actions__cta {
    grid-column: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .upload-dropzone,
  .history-table tbody tr,
  .history-card,
  .button,
  .mini-button {
    transition: none;
  }

  .analysis-steps__dot,
  .history-loading__bar {
    animation: none;
  }

  .upload-dropzone:focus-visible {
    scroll-behavior: auto;
  }
}
</style>
