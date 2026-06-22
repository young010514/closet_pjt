import { createRouter, createWebHistory } from 'vue-router'

import BusinessSignupView from '@/views/BusinessSignupView.vue'
import CommunityDetailView from '@/views/CommunityDetailView.vue'
import CommunityFormView from '@/views/CommunityFormView.vue'
import CommunityListView from '@/views/CommunityListView.vue'
import LoginView from '@/views/LoginView.vue'
import MyPageView from '@/views/MyPageView.vue'
import NormalSignupView from '@/views/NormalSignupView.vue'
import SignupSelectView from '@/views/SignupSelectView.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),

  routes: [
    {
      path: '/',
      redirect: '/mypage',
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true },
    },
    {
      path: '/signup',
      name: 'signup',
      component: SignupSelectView,
      meta: { guestOnly: true },
    },
    {
      path: '/signup/normal',
      name: 'signup-normal',
      component: NormalSignupView,
      meta: { guestOnly: true },
    },
    {
      path: '/signup/business',
      name: 'signup-business',
      component: BusinessSignupView,
      meta: { guestOnly: true },
    },
    {
      path: '/mypage',
      name: 'mypage',
      component: MyPageView,
      meta: { requiresAuth: true },
    },
    {
      path: '/community',
      name: 'community',
      component: CommunityListView,
    },
    {
      path: '/community/new',
      name: 'community-new',
      component: CommunityFormView,
    },
    {
      path: '/community/:pk',
      name: 'community-detail',
      component: CommunityDetailView,
    },
    {
      path: '/community/:pk/edit',
      name: 'community-edit',
      component: CommunityFormView,
      props: { isEdit: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (!authStore.isInitialized) {
    await authStore.initializeAuth()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return { name: 'mypage' }
  }

  return true
})

export default router
