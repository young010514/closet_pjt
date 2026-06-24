<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const logoutError = ref('')
const isLoggingOut = ref(false)
const searchInput = ref('')


const isAuthenticated = computed(() => authStore.isAuthenticated)
const isBusinessUser = computed(() => authStore.isBusinessUser)
const VALID_BOARDS = ['fashion', 'daily', 'local_shop', 'experience']

function normalizeBoard(value) {
  const board = Array.isArray(value) ? value[0] : value
  return VALID_BOARDS.includes(board) ? board : 'fashion'
}
const goUserSearch = () =>{
  router.push('/users/search')
}

const normalizedBoard = computed(() => normalizeBoard(route.params.board))
const isCommunityNavActive = computed(() => {
  // if (route.name === 'community') {
  //   return normalizedBoard.value !== 'local_shop'
  // }

  // return ['community-new', 'community-detail', 'community-edit'].includes(String(route.name))
const communityRoutes = [
    'community', 
    'community-new', 
    'community-detail', 
    'community-edit'
  ]
  
  // 2. 현재 페이지(route.name)가 이 배열에 포함되어 있다면 무조건 true를 반환합니다.
  return communityRoutes.includes(String(route.name))
})

function normalizeSearchTerm(value) {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

function submitHeaderSearch() {
  const term = searchInput.value.trim()
  if (!term) {
    return
  }

  router.push({
    name: 'user-search',
    query: { q: term },
  })
}

async function logout() {
  if (!window.confirm('로그아웃 하시겠습니까?')) return

  logoutError.value = ''
  isLoggingOut.value = true

  try {
    await authStore.logout()
  } catch (error) {
    logoutError.value = error.message || '로그아웃 요청을 처리하지 못했습니다.'
  } finally {
    isLoggingOut.value = false
    router.push('/login')
  }
}

watch(
  () => route.query.q,
  (value) => {
    searchInput.value = normalizeSearchTerm(value)
  },
  { immediate: true },
)
</script>

<template>
  <div class="app-shell">
<header class="topbar">
  <RouterLink class="brand-link" to="/">Closet</RouterLink>

  <nav class="topnav topnav--center" aria-label="커뮤니티 메뉴">
    <RouterLink
      class="topnav-link"
      active-class="topnav-link--active"
      to="/community/fashion"
    >
      패션 정보 공유
    </RouterLink>

    <RouterLink
      class="topnav-link"
      active-class="topnav-link--active"
      to="/community/daily"
    >
      일상 &amp; 소통
    </RouterLink>

    <RouterLink
      class="topnav-link"
      active-class="topnav-link--active"
      to="/community/local_shop"
    >
      우리 동네 가게
    </RouterLink>

    <RouterLink
      class="topnav-link"
      active-class="topnav-link--active"
      to="/community/experience"
    >
      체험단
    </RouterLink>
  </nav>

  <nav class="topnav topnav--right" aria-label="사용자 메뉴">
    <template v-if="isAuthenticated">
      <RouterLink v-if="isBusinessUser" class="topnav-link topnav-link--business" :to="{ name: 'business-dashboard' }">
            사업자 대시보드
          </RouterLink>
      <RouterLink class="topnav-link" to="/mypage">
        마이페이지
      </RouterLink>

      <button
        type="button"
        class="nav-button"
        :disabled="isLoggingOut"
        @click="logout"
      >
        {{ isLoggingOut ? '로그아웃 중' : '로그아웃' }}
      </button>
    </template>

    <template v-else>
      <RouterLink class="topnav-link" to="/login">
        로그인
      </RouterLink>

      <RouterLink class="topnav-link" to="/signup/normal">
        회원가입
      </RouterLink>
    </template>

    <button
      type="button"
      class="button button--secondary topbar-search__button"
      aria-label="유저 검색 페이지로 이동"
      @click="goUserSearch"
    >
      검색
    </button>
  </nav>
</header>


    <p v-if="logoutError" class="shell-error" role="alert">{{ logoutError }}</p>

    <RouterView />
  </div>
</template>
