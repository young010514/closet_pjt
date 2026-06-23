<script setup>
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const logoutError = ref('')
const isLoggingOut = ref(false)

const isAuthenticated = computed(() => authStore.isAuthenticated)
const VALID_BOARDS = ['fashion', 'daily', 'local_shop', 'experience']

function normalizeBoard(value) {
  const board = Array.isArray(value) ? value[0] : value
  return VALID_BOARDS.includes(board) ? board : 'fashion'
}

const normalizedBoard = computed(() => normalizeBoard(route.query.board))
const isCommunityNavActive = computed(() => {
  if (route.name === 'community') {
    return normalizedBoard.value !== 'local_shop'
  }

  return ['community-new', 'community-detail', 'community-edit'].includes(String(route.name))
})
const isStoreNavActive = computed(
  () => route.name === 'community' && normalizedBoard.value === 'local_shop',
)

async function logout() {
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
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand-link" to="/">Closet</RouterLink>

      <nav class="topnav" aria-label="주요 메뉴">
        <RouterLink
          class="topnav-link"
          :class="{ 'topnav-link--active': isStoreNavActive }"
          :to="{ name: 'community', query: { board: 'local_shop' } }"
        >
          옷가게 목록
        </RouterLink>
        <template v-if="isAuthenticated">
          <RouterLink
            class="topnav-link"
            :class="{ 'topnav-link--active': isCommunityNavActive }"
            :to="{ name: 'community', query: { board: 'fashion' } }"
          >
            커뮤니티
          </RouterLink>
          <RouterLink to="/mypage">마이페이지</RouterLink>
          <button type="button" class="nav-button" :disabled="isLoggingOut" @click="logout">
            {{ isLoggingOut ? '로그아웃 중' : '로그아웃' }}
          </button>
        </template>
        <template v-else>
          <RouterLink to="/login">로그인</RouterLink>
          <RouterLink to="/signup">회원가입</RouterLink>
        </template>
      </nav>
    </header>

    <p v-if="logoutError" class="shell-error" role="alert">{{ logoutError }}</p>

    <RouterView />
  </div>
</template>
