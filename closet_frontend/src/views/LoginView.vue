<script setup>
import { reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import FormFieldError from '@/components/accounts/FormFieldError.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const form = reactive({
  username: '',
  password: '',
})
const fieldErrors = reactive({})
const formErrors = ref([])
const isSubmitting = ref(false)

function clearErrors() {
  Object.keys(fieldErrors).forEach((key) => delete fieldErrors[key])
  formErrors.value = []
  authStore.clearError()
}

function setFieldError(name, message) {
  fieldErrors[name] = [message]
}

function validateForm() {
  let valid = true

  if (!form.username.trim()) {
    setFieldError('username', '아이디를 입력해 주세요.')
    valid = false
  }

  if (!form.password) {
    setFieldError('password', '비밀번호를 입력해 주세요.')
    valid = false
  }

  if (!valid) {
    formErrors.value = ['입력 내용을 확인해 주세요.']
  }

  return valid
}

function applyApiErrors(error) {
  Object.assign(fieldErrors, error.fieldErrors || {})
  formErrors.value = error.formErrors?.length ? error.formErrors : [error.message || '로그인에 실패했습니다.']
}

function redirectTarget() {
  const candidate = route.query.redirect
  if (typeof candidate === 'string' && candidate.startsWith('/') && !candidate.startsWith('//')) {
    return candidate
  }
  return '/mypage'
}

async function submitLogin() {
  clearErrors()
  if (!validateForm()) return

  isSubmitting.value = true

  try {
    await authStore.login({
      username: form.username.trim(),
      password: form.password,
    })
    if (authStore.isBusinessUser) {
      router.push('/business/dashboard')
    } else {
      router.push(redirectTarget())
    }
  } catch (error) {
    applyApiErrors(error)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="page-view auth-view">
    <section class="panel form-panel">
      <p class="eyebrow">Closet Account</p>
      <h1>로그인</h1>

      <div v-if="formErrors.length" class="alert alert--error" role="alert">
        <p v-for="message in formErrors" :key="message">{{ message }}</p>
      </div>

      <form class="stack-form" @submit.prevent="submitLogin">
        <div class="form-field">
          <label for="login-username">아이디</label>
          <input
            id="login-username"
            v-model="form.username"
            type="text"
            name="username"
            autocomplete="username"
            required
          />
          <FormFieldError :errors="fieldErrors.username" />
        </div>

        <div class="form-field">
          <label for="login-password">비밀번호</label>
          <input
            id="login-password"
            v-model="form.password"
            type="password"
            name="password"
            autocomplete="current-password"
            required
          />
          <FormFieldError :errors="fieldErrors.password" />
        </div>

        <button class="button button--primary" type="submit" :disabled="isSubmitting || authStore.isLoading">
          {{ isSubmitting ? '로그인 중' : '로그인' }}
        </button>
      </form>

      <p class="panel-footer">
        계정이 없다면
        <RouterLink to="/signup">회원가입</RouterLink>
      </p>
    </section>
  </main>
</template>
