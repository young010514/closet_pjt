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
const VALID_BOARDS = ['fashion', 'daily', 'local_shop', 'experience']

function normalizeBoard(value) {
  const board = Array.isArray(value) ? value[0] : value
  return VALID_BOARDS.includes(board) ? board : 'fashion'
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


      <nav class="topnav" aria-label="주요 메뉴">

        <template v-if="isAuthenticated">
          <RouterLink
            class="topnav-link"
            :class="{ 'topnav-link--active': isCommunityNavActive }"
            :to="{ name: 'community', params: { board: 'fashion' } }"
          >
            커뮤니티
          </RouterLink>
          <RouterLink class="topnav-link" to="/mypage">마이페이지</RouterLink>
          <button type="button" class="nav-button" :disabled="isLoggingOut" @click="logout">
            {{ isLoggingOut ? '로그아웃 중' : '로그아웃' }}
          </button>
        </template>
        <template v-else>
          <RouterLink class="topnav-link" to="/login">로그인</RouterLink>
          <RouterLink class="topnav-link" to="/signup">회원가입</RouterLink>
        </template>
      </nav>

      
      <form class="topbar-search" @submit.prevent="submitHeaderSearch">
        <label class="sr-only" for="topbar-user-search">유저 검색</label>
        <input
          id="topbar-user-search"
          v-model="searchInput"
          type="search"
          placeholder="유저 검색"
          autocomplete="off"
          aria-label="유저 검색어 입력"
        />
        <button
          type="submit"
          class="button button--secondary topbar-search__button"
          aria-label="유저 검색 실행"
        >
          검색
        </button>
      </form>
    </header>

    <p v-if="logoutError" class="shell-error" role="alert">{{ logoutError }}</p>

    <RouterView />
  </div>
</template>
