<script setup>
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const logoutError = ref('')
const isLoggingOut = ref(false)

const isAuthenticated = computed(() => authStore.isAuthenticated)

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
        <template v-if="isAuthenticated">
          <RouterLink to="/community">커뮤니티</RouterLink>
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
