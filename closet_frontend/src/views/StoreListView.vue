<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { normalizeApiError } from '@/api/accounts'
import { getDongs, getSigungus, getSidos } from '@/api/regions'
import { STORE_PAGE_SIZE, getStores } from '@/api/stores'

import StoreCard from '@/components/stores/StoreCard.vue'
import StorePagination from '@/components/stores/StorePagination.vue'

const filters = reactive({
  search: '',
  sido: '',
  sigungu: '',
  dong: '',
  ordering: 'name',
})

const mapBounds = reactive({
  minLat: '',
  maxLat: '',
  minLng: '',
  maxLng: '',
})

const regionOptions = reactive({
  sidos: [],
  sigungus: [],
  dongs: [],
})

const stores = ref([])
const totalCount = ref(0)
const pageSize = ref(STORE_PAGE_SIZE)
const currentPage = ref(1)
const isLoadingStores = ref(false)
const isLoadingSidos = ref(false)
const isLoadingSigungus = ref(false)
const isLoadingDongs = ref(false)
const regionError = ref('')
const storeError = ref('')

const formattedTotalCount = computed(() => new Intl.NumberFormat('ko-KR').format(totalCount.value))
const pageCount = computed(() => Math.max(1, Math.ceil(totalCount.value / pageSize.value || 1)))
const hasMapBounds = computed(() =>
  [mapBounds.minLat, mapBounds.maxLat, mapBounds.minLng, mapBounds.maxLng].every(
    (value) => value !== '' && value !== null && value !== undefined,
  ),
)

const defaultFilters = {
  search: '',
  sido: '',
  sigungu: '',
  dong: '',
  ordering: 'name',
}

const hasFilterChanges = computed(
  () =>
    filters.search !== defaultFilters.search ||
    filters.sido !== defaultFilters.sido ||
    filters.sigungu !== defaultFilters.sigungu ||
    filters.dong !== defaultFilters.dong ||
    filters.ordering !== defaultFilters.ordering,
)

function buildQueryParams(page = 1) {
  const params = {
    page,
    page_size: STORE_PAGE_SIZE,
    ordering: filters.ordering,
  }

  const search = filters.search.trim()
  if (search) {
    params.search = search
  }

  if (filters.sido) {
    params.sido = filters.sido
  }

  if (filters.sigungu) {
    params.sigungu = filters.sigungu
  }

  if (filters.dong) {
    params.dong = filters.dong
  }

  if (hasMapBounds.value) {
    params.min_lat = mapBounds.minLat
    params.max_lat = mapBounds.maxLat
    params.min_lng = mapBounds.minLng
    params.max_lng = mapBounds.maxLng
  }

  return params
}

function resetLowerRegions(level) {
  if (level === 'sido') {
    filters.sigungu = ''
    filters.dong = ''
    regionOptions.sigungus = []
    regionOptions.dongs = []
    return
  }

  if (level === 'sigungu') {
    filters.dong = ''
    regionOptions.dongs = []
  }
}

async function loadSidos() {
  isLoadingSidos.value = true
  regionError.value = ''

  try {
    const data = await getSidos()
    regionOptions.sidos = Array.isArray(data.sidos) ? data.sidos : []
  } catch (error) {
    const normalized = normalizeApiError(error)
    regionOptions.sidos = []
    regionError.value = `${normalized.message} 지역 필터를 불러오지 못했습니다.`
  } finally {
    isLoadingSidos.value = false
  }
}

async function loadSigungus() {
  if (!filters.sido) {
    regionOptions.sigungus = []
    regionError.value = ''
    return
  }

  isLoadingSigungus.value = true

  try {
    const data = await getSigungus(filters.sido)
    regionOptions.sigungus = Array.isArray(data.sigungus) ? data.sigungus : []
    regionError.value = ''
  } catch (error) {
    const normalized = normalizeApiError(error)
    regionOptions.sigungus = []
    regionError.value = `${normalized.message} 시군구 목록을 불러오지 못했습니다.`
  } finally {
    isLoadingSigungus.value = false
  }
}

async function loadDongs() {
  if (!filters.sido || !filters.sigungu) {
    regionOptions.dongs = []
    regionError.value = ''
    return
  }

  isLoadingDongs.value = true

  try {
    const data = await getDongs(filters.sido, filters.sigungu)
    regionOptions.dongs = Array.isArray(data.regions) ? data.regions : []
    regionError.value = ''
  } catch (error) {
    const normalized = normalizeApiError(error)
    regionOptions.dongs = []
    regionError.value = `${normalized.message} 동 목록을 불러오지 못했습니다.`
  } finally {
    isLoadingDongs.value = false
  }
}

async function loadStores(page = 1) {
  isLoadingStores.value = true
  storeError.value = ''
  currentPage.value = page

  try {
    const data = await getStores(buildQueryParams(page))
    stores.value = Array.isArray(data.results) ? data.results : []
    totalCount.value = Number(data.count ?? 0)
    pageSize.value = Number(data.page_size ?? STORE_PAGE_SIZE) || STORE_PAGE_SIZE
    currentPage.value = Number(data.page ?? page) || page
  } catch (error) {
    const normalized = normalizeApiError(error)
    stores.value = []
    totalCount.value = 0
    pageSize.value = STORE_PAGE_SIZE
    storeError.value = normalized.message
  } finally {
    isLoadingStores.value = false
  }
}

function applyFilters() {
  loadStores(1)
}

function resetFilters() {
  filters.search = defaultFilters.search
  filters.sido = defaultFilters.sido
  filters.sigungu = defaultFilters.sigungu
  filters.dong = defaultFilters.dong
  filters.ordering = defaultFilters.ordering
  mapBounds.minLat = ''
  mapBounds.maxLat = ''
  mapBounds.minLng = ''
  mapBounds.maxLng = ''
  regionOptions.sigungus = []
  regionOptions.dongs = []
  applyFilters()
}

function handleSidoChange() {
  resetLowerRegions('sido')
  loadSigungus()
}

function handleSigunguChange() {
  resetLowerRegions('sigungu')
  loadDongs()
}

function handlePageChange(page) {
  loadStores(page)
}

onMounted(async () => {
  await Promise.all([loadSidos(), loadStores(1)])
})
</script>

<template>
  <main class="page-view store-view">
    <section class="panel store-panel">
      <div class="page-header-row store-hero">
        <div>
          <p class="eyebrow">Neighborhood Stores</p>
          <h1>동네 옷가게 목록</h1>
          <p class="lead-text">
            시도, 시군구, 동과 상호명 검색으로 원하는 옷가게를 빠르게 찾을 수 있습니다.
          </p>
        </div>

        <div class="store-counter" aria-label="옷가게 수">
          <strong>{{ formattedTotalCount }}</strong>
          <span>개 가게</span>
        </div>
      </div>

      <section class="info-section store-filter-card">
        <form class="stack-form" @submit.prevent="applyFilters">
          <div class="store-filter-grid">
            <div class="form-field store-filter-grid__search">
              <label for="store-search">상호명 검색</label>
              <input
                id="store-search"
                v-model="filters.search"
                type="search"
                name="search"
                placeholder="예: 종로점, 무신사"
              />
            </div>

            <div class="form-field">
              <label for="store-ordering">정렬</label>
              <select id="store-ordering" v-model="filters.ordering" name="ordering">
                <option value="name">가나다순</option>
                <option value="view_count">조회수순</option>
              </select>
            </div>

            <div class="form-field">
              <label for="store-sido">시도</label>
              <select
                id="store-sido"
                v-model="filters.sido"
                name="sido"
                :disabled="isLoadingSidos"
                @change="handleSidoChange"
              >
                <option value="">전체</option>
                <option v-for="sido in regionOptions.sidos" :key="sido" :value="sido">
                  {{ sido }}
                </option>
              </select>
            </div>

            <div class="form-field">
              <label for="store-sigungu">시군구</label>
              <select
                id="store-sigungu"
                v-model="filters.sigungu"
                name="sigungu"
                :disabled="!filters.sido || isLoadingSigungus"
                @change="handleSigunguChange"
              >
                <option value="">
                  {{ filters.sido ? '전체' : '먼저 시도를 선택해 주세요.' }}
                </option>
                <option
                  v-for="sigungu in regionOptions.sigungus"
                  :key="sigungu"
                  :value="sigungu"
                >
                  {{ sigungu }}
                </option>
              </select>
            </div>

            <div class="form-field">
              <label for="store-dong">동</label>
              <select
                id="store-dong"
                v-model="filters.dong"
                name="dong"
                :disabled="!filters.sigungu || isLoadingDongs"
              >
                <option value="">
                  {{ filters.sigungu ? '전체' : '먼저 시군구를 선택해 주세요.' }}
                </option>
                <option v-for="region in regionOptions.dongs" :key="region.id" :value="region.dong">
                  {{ region.dong }}
                </option>
              </select>
            </div>
          </div>

          <div class="store-filter-actions">
            <button class="button button--primary" type="submit" :disabled="isLoadingStores">
              검색
            </button>
            <button
              class="button button--secondary"
              type="button"
              :disabled="isLoadingStores || !hasFilterChanges"
              @click="resetFilters"
            >
              초기화
            </button>
          </div>
        </form>

        <div v-if="regionError" class="alert alert--info" role="status">{{ regionError }}</div>

        <p class="store-map-note">
          카카오맵 현재 지도 영역 필터는 추후 연동할 예정입니다. 서버는 이미
          <code>min_lat</code>, <code>max_lat</code>, <code>min_lng</code>, <code>max_lng</code>
          를 받을 수 있도록 준비되어 있습니다.
        </p>
      </section>

      <section class="store-results">
        <div class="store-summary">
          <span>{{ formattedTotalCount }}개 결과</span>
          <span v-if="totalCount > 0">페이지 {{ currentPage }} / {{ pageCount }}</span>
        </div>

        <div v-if="storeError" class="alert alert--error" role="alert">
          {{ storeError }}
        </div>

        <p v-if="isLoadingStores" class="muted-text">옷가게 목록을 불러오는 중입니다.</p>

        <div v-else-if="!storeError && !stores.length" class="store-empty">
          조건에 맞는 옷가게가 없습니다.
        </div>

        <div v-else class="store-list">
          <StoreCard v-for="store in stores" :key="store.id" :store="store" />
        </div>

        <StorePagination
          v-if="pageCount > 1 && stores.length && !storeError"
          :page="currentPage"
          :page-count="pageCount"
          :is-loading="isLoadingStores"
          @change="handlePageChange"
        />
      </section>
    </section>
  </main>
</template>
