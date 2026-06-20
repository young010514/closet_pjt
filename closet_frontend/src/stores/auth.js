import { defineStore } from 'pinia'

import { initializeCsrf } from '@/api/http'
import {
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  normalizeApiError,
  signupBusiness as signupBusinessRequest,
  signupNormal as signupNormalRequest,
} from '@/api/accounts'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isInitialized: false,
    isLoading: false,
    error: '',
  }),

  getters: {
    isAuthenticated: (state) => Boolean(state.user),
    isBusinessUser: (state) => state.user?.profile?.user_type === 'business',
    isNormalUser: (state) => state.user?.profile?.user_type === 'normal',
  },

  actions: {
    async initializeAuth() {
      if (this.isInitialized) return this.user

      this.isLoading = true
      this.error = ''

      try {
        await initializeCsrf()

        try {
          this.user = await getCurrentUser()
        } catch (error) {
          const normalized = normalizeApiError(error)
          this.user = null

          if (![401, 403].includes(normalized.status)) {
            this.error = normalized.message
          }
        }
      } finally {
        this.isInitialized = true
        this.isLoading = false
      }

      return this.user
    },

    async fetchCurrentUser() {
      this.isLoading = true
      this.error = ''

      try {
        this.user = await getCurrentUser()
        return this.user
      } catch (error) {
        const normalized = normalizeApiError(error)
        if ([401, 403].includes(normalized.status)) {
          this.user = null
        }
        this.error = normalized.message
        throw normalized
      } finally {
        this.isLoading = false
      }
    },

    async login(credentials) {
      this.isLoading = true
      this.error = ''

      try {
        const data = await loginRequest(credentials)
        this.user = data.user
        return data
      } catch (error) {
        const normalized = normalizeApiError(error)
        this.error = normalized.message
        throw normalized
      } finally {
        this.isLoading = false
      }
    },

    async signupNormal(payload) {
      this.isLoading = true
      this.error = ''

      try {
        const data = await signupNormalRequest(payload)
        this.user = data.user
        return data
      } catch (error) {
        const normalized = normalizeApiError(error)
        this.error = normalized.message
        throw normalized
      } finally {
        this.isLoading = false
      }
    },

    async signupBusiness(payload) {
      this.isLoading = true
      this.error = ''

      try {
        const data = await signupBusinessRequest(payload)
        this.user = data.user
        return data
      } catch (error) {
        const normalized = normalizeApiError(error)
        this.error = normalized.message
        throw normalized
      } finally {
        this.isLoading = false
      }
    },

    async logout() {
      this.isLoading = true
      this.error = ''

      try {
        return await logoutRequest()
      } catch (error) {
        const normalized = normalizeApiError(error)
        this.error = normalized.message
        throw normalized
      } finally {
        this.user = null
        this.isLoading = false
      }
    },

    clearError() {
      this.error = ''
    },
  },
})
