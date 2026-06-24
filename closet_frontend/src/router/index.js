
import { createRouter, createWebHistory } from 'vue-router'

import BusinessSignupView from '@/views/BusinessSignupView.vue'
import CommunityDetailView from '@/views/CommunityDetailView.vue'
import CommunityFormView from '@/views/CommunityFormView.vue'
import CommunityListView from '@/views/CommunityListView.vue'
import LoginView from '@/views/LoginView.vue'
import MyPageView from '@/views/MyPageView.vue'
import NormalSignupView from '@/views/NormalSignupView.vue'
import UserSearchView from '@/views/UserSearchView.vue'
import UserProfileView from '@/views/UserProfileView.vue'
import SignupSelectView from '@/views/SignupSelectView.vue'
import { useAuthStore } from '@/stores/auth'

const VALID_BOARDS = ['fashion', 'daily', 'local_shop', 'experience']
const DEFAULT_BOARD = 'fashion'

function normalizeBoard(value) {
  const board = Array.isArray(value) ? value[0] : value
  return VALID_BOARDS.includes(board) ? board : DEFAULT_BOARD
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),

  routes: [
    {
      path: '/',
      redirect: '/community/local_shop',
    },
    {
      path: '/stores',
      redirect: '/community/local_shop',
    },
    {
      path: '/community',
      redirect: '/community/fashion',
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
      path: '/users/search',
      name: 'user-search',
      component: UserSearchView,
    },
    {
      path: '/users/:userId',
      name: 'user-profile',
      component: UserProfileView,
    },
    {
      path: '/community/new',
      name: 'community-new',
      component: CommunityFormView,
    },
    {
      path: '/community/:pk(\\d+)/edit',
      name: 'community-edit',
      component: CommunityFormView,
      props: { isEdit: true },
    },
    {
      path: '/community/:pk(\\d+)',
      name: 'community-detail',
      component: CommunityDetailView,
    },
    {
      path: '/community/:board([^/]+)',
      name: 'community',
      component: CommunityListView,
    },
    {
      path: '/business/dashboard',
      name: 'business-dashboard',
      component: () => import('@/views/business/BusinessDashboardView.vue'),
      meta: { requiresAuth: true, requiresBusiness: true },
    },
    {
      path: '/business/store',
      name: 'business-store',
      component: () => import('@/views/business/StorePostListView.vue'),
      meta: { requiresAuth: true, requiresBusiness: true },
    },
    {
      path: '/business/store/new',
      name: 'business-store-new',
      component: () => import('@/views/business/StorePostFormView.vue'),
      meta: { requiresAuth: true, requiresBusiness: true },
    },
    {
      path: '/business/store/:pk/edit',
      name: 'business-store-edit',
      component: () => import('@/views/business/StorePostFormView.vue'),
      meta: { requiresAuth: true, requiresBusiness: true },
    },
    {
      path: '/business/experience',
      name: 'business-experience',
      component: () => import('@/views/business/ExperiencePostListView.vue'),
      meta: { requiresAuth: true, requiresBusiness: true },
    },
    {
      path: '/business/experience/new',
      name: 'business-experience-new',
      component: () => import('@/views/business/ExperiencePostFormView.vue'),
      meta: { requiresAuth: true, requiresBusiness: true },
    },
    {
      path: '/business/experience/:pk/edit',
      name: 'business-experience-edit',
      component: () => import('@/views/business/ExperiencePostFormView.vue'),
      meta: { requiresAuth: true, requiresBusiness: true },
    },
    {
      path: '/business/experience/:pk/applicants',
      name: 'business-experience-applicants',
      component: () => import('@/views/business/ExperienceApplicantView.vue'),
      meta: { requiresAuth: true, requiresBusiness: true },
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.path === '/community' && to.query.board) {
    return {
      name: 'community',
      params: { board: normalizeBoard(to.query.board) },
      query: {},
      replace: true,
    }
  }

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

  if (to.meta.requiresBusiness) {
    if (!authStore.isAuthenticated) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    if (!authStore.isBusinessUser) {
      return { name: 'community' }
    }
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return { name: 'mypage' }
  }

  return true
})

export default router
