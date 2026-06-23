<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import { getMyRegions, normalizeApiError } from '@/api/accounts'
import { getDongs, getSigungus, getSidos } from '@/api/regions'
import { STORE_PAGE_SIZE, getStores } from '@/api/stores'
import StoreCard from '@/components/stores/StoreCard.vue'
import StorePagination from '@/components/stores/StorePagination.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const DEFAULT_CENTER = {
  lat: 37.497952,
  lng: 127.027619,
}

const DEFAULT_MAP_LEVEL = 5
const MAP_IDLE_DEBOUNCE_MS = 400

let mapIdleTimer = null
let skipNextMapIdleRefresh = false
let mapIdleHandler = null
let storeRequestSeq = 0
const isUnmounted = ref(false)

const defaultFilters = {
  search: '',
  sido: '',
  sigungu: '',
  dong: '',
  ordering: 'name',
}

const filters = reactive({
  search: defaultFilters.search,
  sido: defaultFilters.sido,
  sigungu: defaultFilters.sigungu,
  dong: defaultFilters.dong,
  ordering: defaultFilters.ordering,
})

const mapBounds = reactive({
  swLat: null,
  swLng: null,
  neLat: null,
  neLng: null,
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
const isLoadingMap = ref(true)
const regionError = ref('')
const storeError = ref('')
const mapError = ref('')
const useCurrentBounds = ref(true)
const selectedStoreId = ref(null)

const mapContainer = ref(null)
const map = ref(null)
const mapMarkers = ref([])

const storeCardRefs = new Map()

const formattedTotalCount = computed(() =>
  new Intl.NumberFormat('ko-KR').format(totalCount.value),
)

const pageCount = computed(() => Math.max(1, Math.ceil(totalCount.value / (pageSize.value || 1))))

const hasFilterChanges = computed(
  () =>
    filters.search !== defaultFilters.search ||
    filters.sido !== defaultFilters.sido ||
    filters.sigungu !== defaultFilters.sigungu ||
    filters.dong !== defaultFilters.dong ||
    filters.ordering !== defaultFilters.ordering ||
    useCurrentBounds.value !== true,
)

const hasMapBounds = computed(() =>
  [mapBounds.swLat, mapBounds.swLng, mapBounds.neLat, mapBounds.neLng].every((value) =>
    Number.isFinite(value),
  ),
)

const canQueryByMapBounds = computed(() => useCurrentBounds.value && hasMapBounds.value)

function getStoreKey(store) {
  return String(store?.id ?? '')
}

function isSelectedStore(store) {
  return selectedStoreId.value !== null && getStoreKey(store) === selectedStoreId.value
}

function getStoreDisplayName(store) {
  return store?.display_name || store?.name || '이름 없음'
}

function getStoreCoordinates(store) {
  const latitude = Number(store?.latitude ?? store?.lat)
  const longitude = Number(store?.longitude ?? store?.lng ?? store?.lon)

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    return null
  }

  return {
    lat: latitude,
    lng: longitude,
  }
}

function clearMapIdleTimer() {
  if (mapIdleTimer !== null) {
    clearTimeout(mapIdleTimer)
    mapIdleTimer = null
  }
}

function clearMapMarkers() {
  mapMarkers.value.forEach((marker) => {
    marker.setMap(null)
  })

  mapMarkers.value = []
}

function setStoreCardRef(storeId) {
  return (element) => {
    const key = String(storeId)

    if (element instanceof HTMLElement) {
      storeCardRefs.set(key, element)
      return
    }

    storeCardRefs.delete(key)
  }
}

function scrollStoreCardIntoView(storeId) {
  const element = storeCardRefs.get(String(storeId))

  if (!element) {
    return
  }

  element.scrollIntoView({
    behavior: 'smooth',
    block: 'center',
    inline: 'nearest',
  })
}

function createMarkerImage(kakao, isActive) {
  const color = isActive ? '#d97706' : '#2f7d6d'
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="44" viewBox="0 0 32 44" fill="none">
      <path d="M16 42s10-12.5 10-22A10 10 0 1 0 6 20c0 9.5 10 22 10 22z" fill="${color}" />
      <circle cx="16" cy="20" r="4.5" fill="#fff" />
    </svg>
  `
  const src = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`

  return new kakao.maps.MarkerImage(src, new kakao.maps.Size(32, 44), {
    offset: new kakao.maps.Point(16, 44),
  })
}

function renderStoreMarkers() {
  clearMapMarkers()

  if (!map.value || !window.kakao?.maps) {
    return
  }

  stores.value.forEach((store) => {
    const coordinates = getStoreCoordinates(store)

    if (!coordinates) {
      return
    }

    const marker = new window.kakao.maps.Marker({
      map: map.value,
      position: new window.kakao.maps.LatLng(coordinates.lat, coordinates.lng),
      title: getStoreDisplayName(store),
      zIndex: isSelectedStore(store) ? 10 : 1,
      image: createMarkerImage(window.kakao, isSelectedStore(store)),
    })

    window.kakao.maps.event.addListener(marker, 'click', () => {
      void selectStore(store, { panToMap: true, scrollToCard: true })
    })

    mapMarkers.value.push(marker)
  })
}

function captureMapBounds() {
  if (!map.value || !window.kakao?.maps) {
    return false
  }

  const bounds = map.value.getBounds()
  const southWest = bounds.getSouthWest()
  const northEast = bounds.getNorthEast()

  mapBounds.swLat = southWest.getLat()
  mapBounds.swLng = southWest.getLng()
  mapBounds.neLat = northEast.getLat()
  mapBounds.neLng = northEast.getLng()

  return true
}

function scheduleStoreReloadFromBounds() {
  if (isUnmounted.value) {
    return
  }

  clearMapIdleTimer()

  mapIdleTimer = window.setTimeout(() => {
    if (isUnmounted.value) {
      return
    }

    mapIdleTimer = null
    void loadStores(1)
  }, MAP_IDLE_DEBOUNCE_MS)
}

function handleMapIdle() {
  if (isUnmounted.value) {
    return
  }

  captureMapBounds()

  if (skipNextMapIdleRefresh) {
    skipNextMapIdleRefresh = false
    return
  }

  if (useCurrentBounds.value) {
    scheduleStoreReloadFromBounds()
  }
}

function focusMapOnStore(store) {
  if (isUnmounted.value) {
    return
  }

  if (!map.value || !window.kakao?.maps) {
    return
  }

  const coordinates = getStoreCoordinates(store)

  if (!coordinates) {
    return
  }

  clearMapIdleTimer()
  skipNextMapIdleRefresh = true
  map.value.panTo(new window.kakao.maps.LatLng(coordinates.lat, coordinates.lng))
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
    if (isUnmounted.value) {
      return
    }

    regionOptions.sidos = Array.isArray(data.sidos) ? data.sidos : []
  } catch (error) {
    if (isUnmounted.value) {
      return
    }

    const normalized = normalizeApiError(error)
    regionOptions.sidos = []
    regionError.value = `${normalized.message} 시도 목록을 불러오지 못했습니다.`
  } finally {
    if (!isUnmounted.value) {
      isLoadingSidos.value = false
    }
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
    if (isUnmounted.value) {
      return
    }

    regionOptions.sigungus = Array.isArray(data.sigungus) ? data.sigungus : []
    regionError.value = ''
  } catch (error) {
    if (isUnmounted.value) {
      return
    }

    const normalized = normalizeApiError(error)
    regionOptions.sigungus = []
    regionError.value = `${normalized.message} 시군구 목록을 불러오지 못했습니다.`
  } finally {
    if (!isUnmounted.value) {
      isLoadingSigungus.value = false
    }
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
    if (isUnmounted.value) {
      return
    }

    regionOptions.dongs = Array.isArray(data.regions) ? data.regions : []
    regionError.value = ''
  } catch (error) {
    if (isUnmounted.value) {
      return
    }

    const normalized = normalizeApiError(error)
    regionOptions.dongs = []
    regionError.value = `${normalized.message} 동 목록을 불러오지 못했습니다.`
  } finally {
    if (!isUnmounted.value) {
      isLoadingDongs.value = false
    }
  }
}

function buildQueryParams(page = 1) {
  const params = {
    page,
    page_size: pageSize.value || STORE_PAGE_SIZE,
    ordering: filters.ordering,
  }

  const search = filters.search.trim()
  if (search) {
    params.q = search
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

  if (canQueryByMapBounds.value) {
    params.sw_lat = mapBounds.swLat
    params.sw_lng = mapBounds.swLng
    params.ne_lat = mapBounds.neLat
    params.ne_lng = mapBounds.neLng
  }

  return params
}

async function loadStores(page = 1) {
  if (isUnmounted.value) {
    return
  }

  const requestId = ++storeRequestSeq
  isLoadingStores.value = true
  storeError.value = ''
  currentPage.value = page

  try {
    const data = await getStores(buildQueryParams(page))

    if (requestId !== storeRequestSeq) {
      return
    }

    if (isUnmounted.value) {
      return
    }

    stores.value = Array.isArray(data.results) ? data.results : []
    totalCount.value = Number(data.count ?? 0)
    pageSize.value = Number(data.page_size ?? STORE_PAGE_SIZE) || STORE_PAGE_SIZE
    currentPage.value = Number(data.page ?? page) || page

    if (
      selectedStoreId.value &&
      !stores.value.some((store) => getStoreKey(store) === selectedStoreId.value)
    ) {
      selectedStoreId.value = null
    }

    renderStoreMarkers()
  } catch (error) {
    if (requestId !== storeRequestSeq) {
      return
    }

    if (isUnmounted.value) {
      return
    }

    const normalized = normalizeApiError(error)
    stores.value = []
    totalCount.value = 0
    pageSize.value = STORE_PAGE_SIZE
    selectedStoreId.value = null
    clearMapMarkers()
    storeError.value = normalized.message
  } finally {
    if (requestId === storeRequestSeq && !isUnmounted.value) {
      isLoadingStores.value = false
    }
  }
}

function loadStoresForCurrentView(page = 1) {
  clearMapIdleTimer()
  void loadStores(page)
}

function applyFilters() {
  loadStoresForCurrentView(1)
}

function resetFilters() {
  filters.search = defaultFilters.search
  filters.sido = defaultFilters.sido
  filters.sigungu = defaultFilters.sigungu
  filters.dong = defaultFilters.dong
  filters.ordering = defaultFilters.ordering
  useCurrentBounds.value = true
  regionOptions.sigungus = []
  regionOptions.dongs = []
  regionError.value = ''
  selectedStoreId.value = null
  loadStoresForCurrentView(1)
}

function handleSidoChange() {
  resetLowerRegions('sido')
  void loadSigungus()
}

function handleSigunguChange() {
  resetLowerRegions('sigungu')
  void loadDongs()
}

function handlePageChange(page) {
  loadStoresForCurrentView(page)
}

function handleMapBoundsToggle() {
  if (map.value) {
    captureMapBounds()
  }

  loadStoresForCurrentView(1)
}

async function geocodeAddress(kakao, address) {
  return await new Promise((resolve) => {
    try {
      const geocoder = new kakao.maps.services.Geocoder()

      geocoder.addressSearch(address, (results, status) => {
        if (status === kakao.maps.services.Status.OK && Array.isArray(results) && results.length) {
          const [first] = results
          const latitude = Number(first.y)
          const longitude = Number(first.x)

          if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
            resolve({
              lat: latitude,
              lng: longitude,
            })
            return
          }
        }

        resolve(null)
      })
    } catch (error) {
      resolve(null)
    }
  })
}

async function resolveInitialCenter(kakao) {
  if (isUnmounted.value) {
    return DEFAULT_CENTER
  }

  if (!authStore.isInitialized) {
    try {
      await authStore.initializeAuth()
    } catch (error) {
      // initializeAuth() already normalizes recoverable auth failures.
    }
  }

  if (isUnmounted.value) {
    return DEFAULT_CENTER
  }

  if (!authStore.isAuthenticated) {
    return DEFAULT_CENTER
  }

  try {
    const data = await getMyRegions()
    if (isUnmounted.value) {
      return DEFAULT_CENTER
    }

    const regions = Array.isArray(data.regions) ? data.regions : []

    if (!regions.length) {
      return DEFAULT_CENTER
    }

    const primaryRegion = [...regions].sort((left, right) => {
      const leftPriority = Number(left?.priority)
      const rightPriority = Number(right?.priority)

      const normalizedLeft = Number.isFinite(leftPriority)
        ? leftPriority
        : Number.POSITIVE_INFINITY
      const normalizedRight = Number.isFinite(rightPriority)
        ? rightPriority
        : Number.POSITIVE_INFINITY

      return normalizedLeft - normalizedRight
    })[0]

    const address = [primaryRegion?.sido, primaryRegion?.sigungu, primaryRegion?.dong]
      .filter(Boolean)
      .join(' ')
      .trim()

    if (!address) {
      return DEFAULT_CENTER
    }

    const center = await geocodeAddress(kakao, address)
    return center || DEFAULT_CENTER
  } catch (error) {
    return DEFAULT_CENTER
  }
}

function loadKakaoMapsSdk() {
  if (
    window.kakao?.maps?.Map &&
    window.kakao?.maps?.LatLng &&
    window.kakao?.maps?.services?.Geocoder
  ) {
    return Promise.resolve(window.kakao)
  }

  if (window.__closetKakaoMapsLoaderPromise) {
    return window.__closetKakaoMapsLoaderPromise
  }

  const appKey = import.meta.env.VITE_KAKAO_MAP_APP_KEY

  if (!appKey) {
    return Promise.reject(
      new Error('카카오 지도 JavaScript 키가 설정되지 않았습니다. VITE_KAKAO_MAP_APP_KEY를 확인해 주세요.'),
    )
  }

  const existingScript = document.querySelector('script[data-kakao-maps-sdk="true"]')

  window.__closetKakaoMapsLoaderPromise = new Promise((resolve, reject) => {
    const finish = () => {
      if (!window.kakao?.maps?.load) {
        reject(new Error('카카오 지도 SDK를 초기화하지 못했습니다.'))
        return
      }

      window.kakao.maps.load(() => {
        if (
          window.kakao?.maps?.Map &&
          window.kakao?.maps?.LatLng &&
          window.kakao?.maps?.services?.Geocoder
        ) {
          resolve(window.kakao)
          return
        }

        reject(new Error('카카오 지도 SDK를 초기화하지 못했습니다.'))
      })
    }

    if (window.kakao?.maps?.load) {
      finish()
      return
    }

    if (existingScript) {
      existingScript.addEventListener('load', finish, { once: true })
      existingScript.addEventListener(
        'error',
        () => reject(new Error('카카오 지도를 불러오지 못했습니다.')),
        { once: true },
      )
      return
    }

    const script = document.createElement('script')
    script.async = true
    script.dataset.kakaoMapsSdk = 'true'
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(appKey)}&autoload=false&libraries=services`
    script.onload = finish
    script.onerror = () => reject(new Error('카카오 지도를 불러오지 못했습니다.'))
    document.head.appendChild(script)
  }).catch((error) => {
    window.__closetKakaoMapsLoaderPromise = null
    throw error
  })

  return window.__closetKakaoMapsLoaderPromise
}

async function initializeMapAndLoadStores() {
  isLoadingMap.value = true
  mapError.value = ''

  try {
    const kakao = await loadKakaoMapsSdk()
    if (isUnmounted.value) {
      return
    }

    await nextTick()

    if (isUnmounted.value) {
      return
    }

    const center = await resolveInitialCenter(kakao)
    if (isUnmounted.value) {
      return
    }

    if (!mapContainer.value) {
      throw new Error('지도를 표시할 공간을 찾을 수 없습니다.')
    }

    map.value = new kakao.maps.Map(mapContainer.value, {
      center: new kakao.maps.LatLng(center.lat, center.lng),
      level: DEFAULT_MAP_LEVEL,
    })

    captureMapBounds()
    await loadStores(1)

    if (isUnmounted.value || !map.value) {
      return
    }

    mapIdleHandler = handleMapIdle
    kakao.maps.event.addListener(map.value, 'idle', mapIdleHandler)
  } catch (error) {
    if (isUnmounted.value) {
      return
    }

    mapError.value = error instanceof Error ? error.message : '카카오 지도를 불러오지 못했습니다.'
    map.value = null
    clearMapMarkers()
    await loadStores(1)
  } finally {
    if (!isUnmounted.value) {
      isLoadingMap.value = false
    }
  }
}

async function selectStore(store, { panToMap = true, scrollToCard = false } = {}) {
  if (isUnmounted.value) {
    return
  }

  const key = getStoreKey(store)

  if (!key) {
    return
  }

  selectedStoreId.value = key

  if (panToMap) {
    focusMapOnStore(store)
  }

  renderStoreMarkers()

  if (scrollToCard) {
    await nextTick()
    if (isUnmounted.value) {
      return
    }

    scrollStoreCardIntoView(key)
  }
}

onMounted(() => {
  void Promise.all([loadSidos(), initializeMapAndLoadStores()])
})

onBeforeUnmount(() => {
  isUnmounted.value = true
  clearMapIdleTimer()
  skipNextMapIdleRefresh = false

  if (map.value && mapIdleHandler && window.kakao?.maps?.event?.removeListener) {
    window.kakao.maps.event.removeListener(map.value, 'idle', mapIdleHandler)
  }

  clearMapMarkers()
  storeCardRefs.clear()
  mapIdleHandler = null
  map.value = null
})
</script>

<template>
  <section class="store-explorer-view store-view">
    <div class="panel store-panel">
      <div class="page-header-row store-hero">
        <div>
          <p class="eyebrow">Neighborhood Stores</p>
          <h1>동네 옷가게 목록</h1>
          <p class="lead-text">
            지역 필터, 지도 영역, 정렬을 함께 써서 원하는 옷가게를 빠르게 찾을 수 있습니다.
          </p>
        </div>

        <div class="store-counter" aria-label="가게 수">
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
                placeholder="상호명, 브랜드명, 키워드"
              />
            </div>

            <div class="form-field">
              <label for="store-ordering">정렬</label>
              <select id="store-ordering" v-model="filters.ordering" name="ordering">
                <option value="name">가나다순</option>
                <option value="view_count">조회순</option>
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
                  {{ filters.sido ? '전체' : '먼저 시도를 선택해 주세요' }}
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
                  {{ filters.sigungu ? '전체' : '먼저 시군구를 선택해 주세요' }}
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

        <div v-if="regionError" class="alert alert--info" role="status">
          {{ regionError }}
        </div>
      </section>

      <div class="store-explorer">
        <section class="info-section store-results store-results-panel">
          <div class="store-summary">
            <span>총 {{ formattedTotalCount }}개 결과</span>
            <span v-if="totalCount > 0">현재 {{ currentPage }} / {{ pageCount }}페이지</span>
          </div>

          <div v-if="storeError" class="alert alert--error" role="alert">
            {{ storeError }}
          </div>

          <p v-if="isLoadingStores" class="muted-text">가게 목록을 불러오는 중입니다.</p>

          <div v-else-if="!storeError && !stores.length" class="store-empty">
            조건에 맞는 옷가게가 없습니다.
          </div>

          <div v-else class="store-list">
            <div
              v-for="store in stores"
              :key="store.id"
              :ref="setStoreCardRef(store.id)"
              :class="['store-card-shell', { 'store-card-shell--active': isSelectedStore(store) }]"
              role="button"
              tabindex="0"
              :aria-pressed="isSelectedStore(store)"
              :aria-label="`${getStoreDisplayName(store)} 선택`"
              @click="selectStore(store)"
              @keydown.enter.prevent="selectStore(store)"
              @keydown.space.prevent="selectStore(store)"
            >
              <StoreCard :store="store" />
            </div>
          </div>

          <StorePagination
            v-if="pageCount > 1 && stores.length && !storeError"
            :page="currentPage"
            :page-count="pageCount"
            :is-loading="isLoadingStores"
            @change="handlePageChange"
          />
        </section>

        <section class="info-section store-map-panel">
          <div class="store-map-header">
            <div>
              <p class="eyebrow">Map View</p>
              <h2>지도에서 보기</h2>
            </div>

            <label class="store-map-toggle">
              <input
                v-model="useCurrentBounds"
                type="checkbox"
                @change="handleMapBoundsToggle"
              />
              <span>현재 지도 영역 내의 가게만 보기</span>
            </label>
          </div>

          <p class="store-map-status">
            <span v-if="useCurrentBounds">현재 지도 영역 기준으로 가게 목록을 보여줍니다.</span>
            <span v-else>지도 영역 필터가 꺼져 있습니다. 전체 목록을 보여줍니다.</span>
          </p>

          <div class="store-map-frame">
            <div ref="mapContainer" class="store-map"></div>

            <div v-if="isLoadingMap" class="store-map-overlay" aria-live="polite">
              카카오 지도를 불러오는 중입니다.
            </div>

            <div v-else-if="mapError" class="store-map-overlay store-map-overlay--error" role="alert">
              {{ mapError }}
            </div>
          </div>

          <p class="store-map-note">
            지도를 움직이면 현재 화면 영역 기준으로 목록이 다시 검색됩니다. 가게 카드를 누르면
            해당 위치로 지도가 이동합니다.
          </p>
        </section>
      </div>
    </div>
  </section>
</template>

<style scoped>
.store-explorer-view {
  margin-top: 1rem;
}
</style>
