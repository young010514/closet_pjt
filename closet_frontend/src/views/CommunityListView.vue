<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { getMyRegions, normalizeApiError } from '@/api/accounts'
import { getDongs, getSigungus, getSidos } from '@/api/regions'
import { STORE_PAGE_SIZE, getStores } from '@/api/stores'
import { useAuthStore } from '@/stores/auth'
import { useCommunityStore } from '@/stores/community'

const communityStore = useCommunityStore()
const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const VALID_BOARDS = ['fashion', 'daily', 'local_shop', 'experience']
const DEFAULT_BOARD = 'fashion'
const numberFormatter = new Intl.NumberFormat('ko-KR')
const storePaginationAriaLabel = '가게 목록 페이지 이동'

function normalizeBoard(value) {
  const board = Array.isArray(value) ? value[0] : value
  return VALID_BOARDS.includes(board) ? board : DEFAULT_BOARD
}

const filters = reactive({
  board: normalizeBoard(route.params.board),
  gender: '',
  category: '',
  ordering: 'latest',
})

const searchInput = ref('')
const appliedSearch = ref('')
const hasSyncedBoard = ref(false)
const isLocalShop = computed(() => filters.board === 'local_shop')
const showSearch = computed(() => !isLocalShop.value)

const BOARD_TABS = [
  { value: 'fashion', label: '패션 정보 공유' },
  { value: 'daily', label: '일상 & 소통' },
  { value: 'local_shop', label: '우리 동네 가게' },
  { value: 'experience', label: '체험단' },
]

const GENDER_OPTIONS = [
  { value: '', label: '성별 전체' },
  { value: 'male', label: '남성' },
  { value: 'female', label: '여성' },
  { value: 'kids', label: '키즈' },
]

const FASHION_CATEGORY_OPTIONS = [
  { value: '', label: '카테고리 전체' },
  { value: 'top', label: '상의' },
  { value: 'bottom', label: '하의' },
  { value: 'outer', label: '아우터' },
  { value: 'shoes', label: '신발' },
  { value: 'accessories', label: '액세서리' },
]

const DAILY_CATEGORY_OPTIONS = [
  { value: '', label: '전체' },
  { value: 'lifestyle', label: '라이프스타일' },
  { value: 'counseling', label: '고민상담' },
]

const EXPERIENCE_CATEGORY_OPTIONS = [
  { value: '', label: '전체' },
  { value: 'recruit', label: '체험단 모집' },
  { value: 'review', label: '체험단 후기' },
]

const ORDERING_OPTIONS = [
  { value: 'latest', label: '최신순' },
  { value: 'popular', label: '인기순' },
  { value: 'viewed', label: '조회순' },
]

const BOARD_LABEL = {
  fashion: '패션 정보 공유',
  daily: '일상 & 소통',
  local_shop: '우리 동네 가게',
  experience: '체험단',
}

const CATEGORY_LABEL = {
  top: '상의',
  bottom: '하의',
  outer: '아우터',
  shoes: '신발',
  accessories: '액세서리',
  lifestyle: '라이프스타일',
  counseling: '고민상담',
  recruit: '체험단 모집',
  review: '체험단 후기',
}

const EXPERIENCE_STATUS_LABEL = {
  recruiting: '모집중',
  closed: '마감',
  ended: '종료',
}

const EXPERIENCE_STATUS_CLASS = {
  recruiting: 'status-recruiting',
  closed: 'status-closed',
  ended: 'status-ended',
}

function selectBoard(value) {
  const nextBoard = normalizeBoard(value)

  if (normalizeBoard(route.params.board) === nextBoard) {
    return
  }

  router.push({
    name: 'community',
    params: { board: nextBoard },
  })
}

function resetBoardFilters() {
  filters.gender = ''
  filters.category = ''
  searchInput.value = ''
  appliedSearch.value = ''
}

function applyPostFilters() {
  const params = { board: filters.board }

  if (filters.gender) params.gender = filters.gender
  if (filters.category) params.category = filters.category
  if (filters.ordering) params.ordering = filters.ordering
  if (appliedSearch.value) params.search = appliedSearch.value

  communityStore.fetchPosts(params)
}

function submitSearch() {
  appliedSearch.value = searchInput.value.trim()
  applyPostFilters()
}

function clearSearch() {
  searchInput.value = ''
  appliedSearch.value = ''
  applyPostFilters()
}

watch(
  () => route.params.board,
  (boardParam) => {
    const normalizedBoard = normalizeBoard(boardParam)
    const rawBoard = Array.isArray(boardParam) ? boardParam[0] : boardParam

    if (rawBoard !== normalizedBoard) {
      router.replace({
        name: 'community',
        params: { board: normalizedBoard },
      })
      return
    }

    const boardChanged = filters.board !== normalizedBoard

    if (boardChanged) {
      filters.board = normalizedBoard
      resetBoardFilters()
    }

    if (!hasSyncedBoard.value || boardChanged) {
      hasSyncedBoard.value = true

      if (normalizedBoard !== 'local_shop') {
        applyPostFilters()
      }
    }
  },
  { immediate: true },
)

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

const defaultStoreFilters = {
  search: '',
  sido: '',
  sigungu: '',
  dong: '',
  ordering: 'name',
}

const storeFilters = reactive({
  search: defaultStoreFilters.search,
  sido: defaultStoreFilters.sido,
  sigungu: defaultStoreFilters.sigungu,
  dong: defaultStoreFilters.dong,
  ordering: defaultStoreFilters.ordering,
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
const isLoadingMap = ref(false)
const regionError = ref('')
const storeError = ref('')
const mapError = ref('')
const useCurrentBounds = ref(true)
const selectedStoreId = ref(null)
const hasInitializedLocalShopFilters = ref(false)

const mapContainer = ref(null)
const map = ref(null)
const mapMarkers = ref([])
const storeCardRefs = new Map()
const isStoreExplorerUnmounted = ref(true)

const formattedTotalCount = computed(() =>
  numberFormatter.format(totalCount.value),
)

const pageCount = computed(() =>
  Math.max(1, Math.ceil(totalCount.value / (pageSize.value || 1))),
)

const hasFilterChanges = computed(
  () =>
    storeFilters.search !== defaultStoreFilters.search ||
    storeFilters.sido !== defaultStoreFilters.sido ||
    storeFilters.sigungu !== defaultStoreFilters.sigungu ||
    storeFilters.dong !== defaultStoreFilters.dong ||
    storeFilters.ordering !== defaultStoreFilters.ordering ||
    useCurrentBounds.value !== true,
)

const hasMapBounds = computed(() =>
  [mapBounds.swLat, mapBounds.swLng, mapBounds.neLat, mapBounds.neLng].every((value) =>
    Number.isFinite(value),
  ),
)

const canQueryByMapBounds = computed(() => useCurrentBounds.value && hasMapBounds.value)

const storePageItems = computed(() => {
  const total = Math.max(1, pageCount.value)
  const current = Math.min(Math.max(currentPage.value, 1), total)

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

  for (let page = start; page <= end; page += 1) {
    items.push(page)
  }

  if (end < total - 1) {
    items.push('ellipsis-end')
  }

  items.push(total)
  return items
})

function getStoreKey(store) {
  return String(store?.id ?? '')
}

function isSelectedStore(store) {
  return selectedStoreId.value !== null && getStoreKey(store) === selectedStoreId.value
}

function getStoreDisplayName(store) {
  return store?.display_name || store?.name || '상호명 없음'
}

function getStoreBranchName(store) {
  return store?.branch_name || ''
}

function getStoreCategoryName(store) {
  return store?.category_name || ''
}

function getStoreRegionLabel(store) {
  return store?.region_label || ''
}

function getStoreAddress(store) {
  return store?.address || store?.road_address || store?.jibun_address || '-'
}

function getStorePhone(store) {
  return store?.phone || ''
}

function formatStoreViewCount(store) {
  return numberFormatter.format(Number(store?.view_count ?? 0))
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
  if (isStoreExplorerUnmounted.value) {
    return
  }

  clearMapIdleTimer()

  mapIdleTimer = window.setTimeout(() => {
    if (isStoreExplorerUnmounted.value) {
      return
    }

    mapIdleTimer = null
    void loadStoresForCurrentView(1)
  }, MAP_IDLE_DEBOUNCE_MS)
}

function handleMapIdle() {
  if (isStoreExplorerUnmounted.value) {
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
  if (isStoreExplorerUnmounted.value) {
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
    storeFilters.sigungu = ''
    storeFilters.dong = ''
    regionOptions.sigungus = []
    regionOptions.dongs = []
    return
  }

  if (level === 'sigungu') {
    storeFilters.dong = ''
    regionOptions.dongs = []
  }
}

async function loadSidos() {
  isLoadingSidos.value = true
  regionError.value = ''

  try {
    const data = await getSidos()

    if (isStoreExplorerUnmounted.value) {
      return
    }

    regionOptions.sidos = Array.isArray(data.sidos) ? data.sidos : []
  } catch (error) {
    if (isStoreExplorerUnmounted.value) {
      return
    }

    const normalized = normalizeApiError(error)
    regionOptions.sidos = []
    regionError.value = `시도 목록을 불러오지 못했습니다. ${normalized.message}`
  } finally {
    if (!isStoreExplorerUnmounted.value) {
      isLoadingSidos.value = false
    }
  }
}

async function loadSigungus() {
  if (!storeFilters.sido) {
    regionOptions.sigungus = []
    regionError.value = ''
    return
  }

  isLoadingSigungus.value = true

  try {
    const data = await getSigungus(storeFilters.sido)

    if (isStoreExplorerUnmounted.value) {
      return
    }

    regionOptions.sigungus = Array.isArray(data.sigungus) ? data.sigungus : []
    regionError.value = ''
  } catch (error) {
    if (isStoreExplorerUnmounted.value) {
      return
    }

    const normalized = normalizeApiError(error)
    regionOptions.sigungus = []
    regionError.value = `시군구 목록을 불러오지 못했습니다. ${normalized.message}`
  } finally {
    if (!isStoreExplorerUnmounted.value) {
      isLoadingSigungus.value = false
    }
  }
}

async function loadDongs() {
  if (!storeFilters.sido || !storeFilters.sigungu) {
    regionOptions.dongs = []
    regionError.value = ''
    return
  }

  isLoadingDongs.value = true

  try {
    const data = await getDongs(storeFilters.sido, storeFilters.sigungu)

    if (isStoreExplorerUnmounted.value) {
      return
    }

    regionOptions.dongs = Array.isArray(data.regions) ? data.regions : []
    regionError.value = ''
  } catch (error) {
    if (isStoreExplorerUnmounted.value) {
      return
    }

    const normalized = normalizeApiError(error)
    regionOptions.dongs = []
    regionError.value = `동 목록을 불러오지 못했습니다. ${normalized.message}`
  } finally {
    if (!isStoreExplorerUnmounted.value) {
      isLoadingDongs.value = false
    }
  }
}

function buildQueryParams(page = 1) {
  const params = {
    page,
    page_size: pageSize.value || STORE_PAGE_SIZE,
    ordering: storeFilters.ordering,
  }

  const search = storeFilters.search.trim()

  if (search) {
    params.q = search
  }

  if (storeFilters.sido) {
    params.sido = storeFilters.sido
  }

  if (storeFilters.sigungu) {
    params.sigungu = storeFilters.sigungu
  }

  if (storeFilters.dong) {
    params.dong = storeFilters.dong
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
  if (isStoreExplorerUnmounted.value) {
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

    if (isStoreExplorerUnmounted.value) {
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

    if (isStoreExplorerUnmounted.value) {
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
    if (requestId === storeRequestSeq && !isStoreExplorerUnmounted.value) {
      isLoadingStores.value = false
    }
  }
}

function loadStoresForCurrentView(page = 1) {
  clearMapIdleTimer()
  void loadStores(page)
}

function applyStoreFilters() {
  loadStoresForCurrentView(1)
}

function resetStoreExplorerStateForUnmount() {
  storeFilters.search = defaultStoreFilters.search
  storeFilters.sido = defaultStoreFilters.sido
  storeFilters.sigungu = defaultStoreFilters.sigungu
  storeFilters.dong = defaultStoreFilters.dong
  storeFilters.ordering = defaultStoreFilters.ordering

  mapBounds.swLat = null
  mapBounds.swLng = null
  mapBounds.neLat = null
  mapBounds.neLng = null

  regionOptions.sidos = []
  regionOptions.sigungus = []
  regionOptions.dongs = []

  stores.value = []
  totalCount.value = 0
  pageSize.value = STORE_PAGE_SIZE
  currentPage.value = 1

  isLoadingStores.value = false
  isLoadingSidos.value = false
  isLoadingSigungus.value = false
  isLoadingDongs.value = false
  isLoadingMap.value = false

  regionError.value = ''
  storeError.value = ''
  mapError.value = ''
  useCurrentBounds.value = true
  selectedStoreId.value = null
  hasInitializedLocalShopFilters.value = false
}

function resetStoreFilters() {
  storeFilters.search = defaultStoreFilters.search
  storeFilters.sido = defaultStoreFilters.sido
  storeFilters.sigungu = defaultStoreFilters.sigungu
  storeFilters.dong = defaultStoreFilters.dong
  storeFilters.ordering = defaultStoreFilters.ordering
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

function sortRegionsByPriority(regions) {
  return [...regions]
    .map((region, index) => ({
      region,
      index,
    }))
    .sort((left, right) => {
      const leftPriority = Number(left.region?.priority)
      const rightPriority = Number(right.region?.priority)

      const normalizedLeft = Number.isFinite(leftPriority)
        ? leftPriority
        : Number.POSITIVE_INFINITY
      const normalizedRight = Number.isFinite(rightPriority)
        ? rightPriority
        : Number.POSITIVE_INFINITY

      if (normalizedLeft !== normalizedRight) {
        return normalizedLeft - normalizedRight
      }

      return left.index - right.index
    })
    .map(({ region }) => region)
}

function pickPrimaryRegion(regions) {
  return sortRegionsByPriority(regions)[0] ?? null
}

function formatRegionAddress(region) {
  return [region?.sido, region?.sigungu, region?.dong].filter(Boolean).join(' ').trim()
}

async function resolveInitialLocalShopContext(kakao) {
  if (isStoreExplorerUnmounted.value) {
    return {
      center: DEFAULT_CENTER,
      primaryRegion: null,
    }
  }

  if (!authStore.isInitialized) {
    try {
      await authStore.initializeAuth()
    } catch (error) {
      // initializeAuth() already normalizes recoverable auth failures.
    }
  }

  if (isStoreExplorerUnmounted.value) {
    return {
      center: DEFAULT_CENTER,
      primaryRegion: null,
    }
  }

  if (!authStore.isAuthenticated) {
    return {
      center: DEFAULT_CENTER,
      primaryRegion: null,
    }
  }

  try {
    const data = await getMyRegions()

    if (isStoreExplorerUnmounted.value) {
      return {
        center: DEFAULT_CENTER,
        primaryRegion: null,
      }
    }

    const primaryRegion = pickPrimaryRegion(Array.isArray(data.regions) ? data.regions : [])

    if (!primaryRegion) {
      return {
        center: DEFAULT_CENTER,
        primaryRegion: null,
      }
    }

    const address = formatRegionAddress(primaryRegion)

    if (!address) {
      return {
        center: DEFAULT_CENTER,
        primaryRegion,
      }
    }

    const center = await geocodeAddress(kakao, address)
    return {
      center: center || DEFAULT_CENTER,
      primaryRegion,
    }
  } catch (error) {
    return {
      center: DEFAULT_CENTER,
      primaryRegion: null,
    }
  }
}

async function applyInitialLocalShopFilters(primaryRegion) {
  if (hasInitializedLocalShopFilters.value || isStoreExplorerUnmounted.value) {
    return false
  }

  const sido = String(primaryRegion?.sido ?? '').trim()
  const sigungu = String(primaryRegion?.sigungu ?? '').trim()
  const dong = String(primaryRegion?.dong ?? '').trim()

  if (!sido || !sigungu || !dong) {
    return false
  }

  hasInitializedLocalShopFilters.value = true
  storeFilters.sido = sido

  await loadSigungus()

  if (isStoreExplorerUnmounted.value) {
    return false
  }

  storeFilters.sigungu = sigungu

  await loadDongs()

  if (isStoreExplorerUnmounted.value) {
    return false
  }

  storeFilters.dong = dong
  return true
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
      new Error('카카오 지도 JavaScript API 키가 설정되어 있지 않습니다. VITE_KAKAO_MAP_APP_KEY를 확인해 주세요.'),
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

    if (isStoreExplorerUnmounted.value) {
      return
    }

    await nextTick()

    if (isStoreExplorerUnmounted.value) {
      return
    }

    const { center, primaryRegion } = await resolveInitialLocalShopContext(kakao)

    if (isStoreExplorerUnmounted.value) {
      return
    }

    if (primaryRegion) {
      await applyInitialLocalShopFilters(primaryRegion)

      if (isStoreExplorerUnmounted.value) {
        return
      }
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

    if (isStoreExplorerUnmounted.value || !map.value) {
      return
    }

    mapIdleHandler = handleMapIdle
    kakao.maps.event.addListener(map.value, 'idle', mapIdleHandler)
  } catch (error) {
    if (isStoreExplorerUnmounted.value) {
      return
    }

    mapError.value = error instanceof Error ? error.message : '카카오 지도를 불러오지 못했습니다.'
    map.value = null
    clearMapMarkers()
    await loadStores(1)
  } finally {
    if (!isStoreExplorerUnmounted.value) {
      isLoadingMap.value = false
    }
  }
}

async function selectStore(store, { panToMap = true, scrollToCard = false } = {}) {
  if (isStoreExplorerUnmounted.value) {
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

    if (isStoreExplorerUnmounted.value) {
      return
    }

    scrollStoreCardIntoView(key)
  }
}

async function mountStoreExplorer() {
  if (!isStoreExplorerUnmounted.value) {
    return
  }

  isStoreExplorerUnmounted.value = false
  isLoadingMap.value = true

  await nextTick()

  if (isStoreExplorerUnmounted.value) {
    return
  }

  void Promise.all([loadSidos(), initializeMapAndLoadStores()])
}

function cleanupStoreExplorer() {
  isStoreExplorerUnmounted.value = true
  clearMapIdleTimer()
  skipNextMapIdleRefresh = false

  if (map.value && mapIdleHandler && window.kakao?.maps?.event?.removeListener) {
    window.kakao.maps.event.removeListener(map.value, 'idle', mapIdleHandler)
  }

  clearMapMarkers()
  storeCardRefs.clear()
  mapIdleHandler = null
  map.value = null
  storeRequestSeq += 1
  resetStoreExplorerStateForUnmount()
}

watch(
  isLocalShop,
  (enabled, previousEnabled) => {
    if (enabled) {
      void mountStoreExplorer()
      return
    }

    if (previousEnabled) {
      cleanupStoreExplorer()
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  cleanupStoreExplorer()
})
</script>

<template>
  <div
    class="community-list"
    :class="{ 'community-list--local-shop': isLocalShop }"
  >


    <template v-if="isLocalShop">
      <section class="store-explorer-view store-view">
        <div class="panel store-panel">
          <div class="page-header-row store-hero">
            <div>
              <p class="eyebrow">Neighborhood Stores</p>
              <h1>우리 동네 가게 목록</h1>
              <p class="lead-text">
                지역, 지도, 정렬을 한 번에 묶어서 원하는 가게를 빠르게 찾을 수 있습니다.
              </p>
            </div>

            <div class="store-counter" aria-label="가게 수">
              <strong>{{ formattedTotalCount }}</strong>
              <span>개 가게</span>
            </div>
          </div>

          <section class="info-section store-filter-card">
            <form class="stack-form" @submit.prevent="applyStoreFilters">
              <div class="store-filter-grid">
                <div class="form-field store-filter-grid__search">
                  <label for="store-search">상호명 검색</label>
                  <input
                    id="store-search"
                    v-model="storeFilters.search"
                    type="search"
                    name="search"
                    placeholder="상호명, 브랜드명, 주소로 검색"
                  />
                </div>

                <div class="form-field">
                  <label for="store-ordering">정렬</label>
                  <select id="store-ordering" v-model="storeFilters.ordering" name="ordering">
                    <option value="name">가나다순</option>
                    <option value="view_count">조회순</option>
                  </select>
                </div>

                <div class="form-field">
                  <label for="store-sido">시도</label>
                  <select
                    id="store-sido"
                    v-model="storeFilters.sido"
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
                    v-model="storeFilters.sigungu"
                    name="sigungu"
                    :disabled="!storeFilters.sido || isLoadingSigungus"
                    @change="handleSigunguChange"
                  >
                    <option value="">
                      {{ storeFilters.sido ? '전체' : '먼저 시도를 선택해 주세요' }}
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
                    v-model="storeFilters.dong"
                    name="dong"
                    :disabled="!storeFilters.sigungu || isLoadingDongs"
                  >
                    <option value="">
                      {{ storeFilters.sigungu ? '전체' : '먼저 시군구를 선택해 주세요' }}
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
                  @click="resetStoreFilters"
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
                조건에 맞는 가게가 없습니다.
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
                  <article class="store-card">
                    <div class="store-card__header">
                      <div class="store-card__title">
                        <h2 class="store-card__name">{{ getStoreDisplayName(store) }}</h2>
                        <p v-if="getStoreBranchName(store)" class="store-card__branch">
                          {{ getStoreBranchName(store) }}
                        </p>
                      </div>

                      <span class="store-chip">조회 {{ formatStoreViewCount(store) }}</span>
                    </div>

                    <div class="store-card__meta">
                      <span v-if="getStoreCategoryName(store)" class="store-chip">
                        {{ getStoreCategoryName(store) }}
                      </span>
                      <span v-if="getStoreRegionLabel(store)" class="store-chip store-chip--ghost">
                        {{ getStoreRegionLabel(store) }}
                      </span>
                    </div>

                    <p class="store-card__address">{{ getStoreAddress(store) }}</p>

                    <div class="store-card__footer">
                      <span v-if="getStorePhone(store)">전화 {{ getStorePhone(store) }}</span>
                      <span>지도로 위치를 확인해 보세요</span>
                    </div>
                  </article>
                </div>
              </div>

              <nav
                v-if="pageCount > 1 && stores.length && !storeError"
                class="store-pagination"
                :aria-label="storePaginationAriaLabel"
              >
                <button
                  type="button"
                  class="mini
                  -button"
                  :disabled="isLoadingStores || currentPage <= 1"
                  @click="handlePageChange(currentPage - 1)"
                >
                  이전
                </button>

                <div class="store-pagination__pages" aria-label="페이지 번호">
                  <template v-for="item in storePageItems" :key="item">
                    <button
                      v-if="typeof item === 'number'"
                      type="button"
                      :class="['mini-button', { 'mini-button--active': item === currentPage }]"
                      :disabled="isLoadingStores || item === currentPage"
                      @click="handlePageChange(item)"
                    >
                      {{ item }}
                    </button>
                    <span v-else class="store-pagination__ellipsis">…</span>
                  </template>
                </div>

                <button
                  type="button"
                  class="mini-button"
                  :disabled="isLoadingStores || currentPage >= pageCount"
                  @click="handlePageChange(currentPage + 1)"
                >
                  다음
                </button>
              </nav>
            </section>

            <section class="info-section store-map-panel">
              <div class="store-map-header">
                <div>
                  <p class="eyebrow">Map View</p>
                  <h2>지도로 보기</h2>
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
                <span v-if="useCurrentBounds">현재 지도 영역을 기준으로 가게 목록을 보여줍니다.</span>
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
                지도를 움직이면 현재 보이는 영역을 기준으로 목록이 다시 갱신됩니다. 가게 카드를 누르면 해당
                위치로 지도가 이동합니다.
              </p>
            </section>
          </div>
        </div>
      </section>
      
    </template>

    <template v-else>
      <div class="filter-section">
        <div class="filter-content">
      <div v-if="filters.board === 'fashion'" class="sub-filters">
        <div class="sub-filter-row">
          <button
            v-for="o in GENDER_OPTIONS"
            :key="o.value"
            class="filter-chip"
            :class="{ active: filters.gender === o.value }"
            @click="filters.gender = o.value; applyPostFilters()"
          >
            {{ o.label }}
          </button>
        </div>
        <div class="sub-filter-row">
          <button
            v-for="o in FASHION_CATEGORY_OPTIONS"
            :key="o.value"
            class="filter-chip"
            :class="{ active: filters.category === o.value }"
            @click="filters.category = o.value; applyPostFilters()"
          >
            {{ o.label }}
          </button>
        </div>
      </div>

      <div v-if="filters.board === 'daily'" class="sub-filters">
        <div class="sub-filter-row">
          <button
            v-for="o in DAILY_CATEGORY_OPTIONS"
            :key="o.value"
            class="filter-chip"
            :class="{ active: filters.category === o.value }"
            @click="filters.category = o.value; applyPostFilters()"
          >
            {{ o.label }}
          </button>
        </div>
      </div>

      <div v-if="filters.board === 'experience'" class="sub-filters">
        <div class="sub-filter-row">
          <button
            v-for="o in EXPERIENCE_CATEGORY_OPTIONS"
            :key="o.value"
            class="filter-chip"
            :class="{ active: filters.category === o.value }"
            @click="filters.category = o.value; applyPostFilters()"
          >
            {{ o.label }}
          </button>
        </div>
      </div>
      </div>
      <RouterLink
        class="btn-write"
        to="/community/new"
      >
        글쓰기
      </RouterLink>
      </div>

      <div class="ordering-row">
        <select v-model="filters.ordering" @change="applyPostFilters">
          <option v-for="o in ORDERING_OPTIONS" :key="o.value" :value="o.value">
            {{ o.label }}
          </option>
        </select>
      </div>

      <div v-if="showSearch" class="search-row">
        <div class="search-box">
          <input
            v-model="searchInput"
            type="search"
            class="search-input"
            placeholder="제목 또는 내용으로 검색"
            @keydown.enter="submitSearch"
          />
          <button
            v-if="searchInput"
            class="btn-search-clear"
            type="button"
            @click="clearSearch"
            aria-label="검색어 지우기"
          >
            ×
          </button>
          <button class="btn-search" type="button" @click="submitSearch">검색</button>
        </div>
        <p v-if="appliedSearch" class="search-applied">
          "<strong>{{ appliedSearch }}</strong>" 검색 결과
          <button class="btn-search-reset" type="button" @click="clearSearch">전체 보기</button>
        </p>
      </div>

      <p v-if="communityStore.isLoading">게시글을 불러오는 중입니다.</p>
      <p v-else-if="communityStore.error" class="error">{{ communityStore.error }}</p>
      <p v-else-if="communityStore.posts.length === 0 && appliedSearch">
        "<strong>{{ appliedSearch }}</strong>"에 대한 검색 결과가 없습니다.
      </p>
      <p v-else-if="communityStore.posts.length === 0">게시글이 없습니다.</p>

      <ul v-else class="post-list">
        <li v-for="post in communityStore.posts" :key="post.id" class="post-item">
          <article class="post-card">
            <div class="post-meta">
              <span class="badge board-badge">{{ BOARD_LABEL[post.board] ?? post.board }}</span>
              <span v-if="post.category" class="badge">
                {{ CATEGORY_LABEL[post.category] ?? post.category }}
              </span>
              <span
                v-if="post.experience_status"
                class="badge status-badge"
                :class="EXPERIENCE_STATUS_CLASS[post.experience_status]"
              >
                {{ EXPERIENCE_STATUS_LABEL[post.experience_status] }}
              </span>
            </div>

            <RouterLink :to="`/community/${post.id}`" class="post-title-link">
              <p class="post-title">{{ post.title }}</p>
            </RouterLink>

            <div class="post-info">
              <RouterLink
                v-if="post.author"
                class="post-author-link"
                :to="{ name: 'user-profile', params: { userId: post.author } }"
              >
                {{ post.author_name }}
              </RouterLink>
              <span v-else>{{ post.author_name }}</span>
              <span>조회 {{ post.view_count }}</span>
              <span>좋아요 {{ post.like_count }}</span>
            </div>
          </article>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.community-list {
  max-width: 1280px;
  margin: 0 auto;
  padding: 1rem;
}

.community-list--local-shop {
  max-width: 1280px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.2rem;
}


.filter-section {
  display: flex;
  align-items: flex-start;
  width: 100%;
  gap: 16px;
}

.filter-content {
  flex: 1;
}

.btn-write {
  margin-left: auto;
  margin-top: 10px;
  flex-shrink: 0;
  padding: 0.4rem 1rem;

  background: #333;
  color: #fff;
  border-radius: 4px;
  text-decoration: none;
}

.board-tabs {
  display: flex;
  border-bottom: 2px solid #eee;
  margin-bottom: 0;
}

.board-tab {
  flex: 1;
  padding: 0.7rem 0.5rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  font-size: 0.95rem;
  color: #666;
  transition: color 0.15s, border-color 0.15s;
}

.board-tab:hover {
  color: #333;
}

.board-tab.active {
  color: #333;
  border-bottom-color: #333;
  font-weight: 600;
}

.sub-filters {
  background: #f8f8f8;
  border: 1px solid #eee;
  border-top: none;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.sub-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.filter-chip {
  padding: 0.3rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 20px;
  background: #fff;
  font-size: 0.82rem;
  cursor: pointer;
  color: #555;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.filter-chip:hover {
  border-color: #999;
}

.filter-chip.active {
  background: #333;
  color: #fff;
  border-color: #333;
}

.ordering-row {
  display: flex;
  justify-content: flex-end;
  margin: 0.75rem 0;
}

.ordering-row select {
  padding: 0.3rem 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.85rem;
}

.search-row {
  margin: 0.5rem 0 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.search-box {
  display: flex;
  gap: 0;
  border: 1px solid #ccc;
  border-radius: 6px;
  overflow: hidden;
}

.search-input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: none;
  outline: none;
  font-size: 0.9rem;
}

.btn-search-clear {
  background: none;
  border: none;
  padding: 0 0.5rem;
  cursor: pointer;
  color: #aaa;
  font-size: 0.85rem;
}

.btn-search-clear:hover {
  color: #555;
}

.btn-search {
  padding: 0.5rem 1rem;
  background: #333;
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 0.88rem;
  font-weight: 600;
  white-space: nowrap;
}

.btn-search:hover {
  background: #111;
}

.search-applied {
  font-size: 0.85rem;
  color: #555;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-search-reset {
  background: none;
  border: none;
  color: #3c5fbe;
  cursor: pointer;
  font-size: 0.82rem;
  text-decoration: underline;
  padding: 0;
}

.post-list {
  list-style: none;
  padding: 0;
}

.post-item {
  border-bottom: 1px solid #eee;
}

.post-card {
  display: grid;
  gap: 0.2rem;
  padding: 0.8rem 0;
}

.post-card:hover {
  background: #f9f9f9;
}

.post-meta {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.3rem;
  align-items: center;
}

.badge {
  font-size: 0.75rem;
  padding: 0.1rem 0.4rem;
  background: #eee;
  border-radius: 3px;
}

.board-badge {
  background: #e8f0fe;
  color: #3c5fbe;
}

.status-badge {
  font-weight: 600;
}

.status-recruiting {
  background: #e6f4ea;
  color: #1e7e34;
}

.status-closed {
  background: #fff3cd;
  color: #856404;
}

.status-ended {
  background: #f8d7da;
  color: #721c24;
}

.post-title-link {
  color: inherit;
  text-decoration: none;
}

.post-title-link:hover .post-title {
  text-decoration: underline;
}

.post-title {
  font-size: 1rem;
  font-weight: 500;
  margin-bottom: 0.3rem;
}

.post-info {
  display: flex;
  gap: 1rem;
  font-size: 0.8rem;
  color: #888;
}

.post-author-link {
  color: inherit;
  font-weight: 600;
  text-decoration: none;
}

.post-author-link:hover {
  text-decoration: underline;
}

.error {
  color: red;
}

.store-explorer-view {
  margin-top: 1rem;
}
</style>
