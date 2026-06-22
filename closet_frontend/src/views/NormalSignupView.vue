<script setup>
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import FormFieldError from '@/components/accounts/FormFieldError.vue'
import TermsAgreement from '@/components/accounts/TermsAgreement.vue'
import UserRegionFields from '@/components/accounts/UserRegionFields.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  email: '',
  password: '',
  password_confirm: '',
  real_name: '',
  nickname: '',
  phone: '',
  birth_date: '',
  gender: 'N',
})
const terms = ref({
  service_terms_agreed: false,
  privacy_agreed: false,
  marketing_agreed: false,
})
const regions = ref([])
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
  const requiredFields = [
    ['username', '아이디'],
    ['email', '이메일'],
    ['password', '비밀번호'],
    ['password_confirm', '비밀번호 확인'],
    ['real_name', '실명'],
    ['nickname', '닉네임'],
    ['phone', '전화번호'],
  ]

  requiredFields.forEach(([name, label]) => {
    if (name.includes('password')) {
      if (!form[name]) {
        setFieldError(name, `${label}을 입력해 주세요.`)
        valid = false
      }
      return
    }

    if (!form[name].trim()) {
      setFieldError(name, `${label}을 입력해 주세요.`)
      valid = false
    }
  })

  if (form.password && form.password_confirm && form.password !== form.password_confirm) {
    setFieldError('password_confirm', '비밀번호가 일치하지 않습니다.')
    valid = false
  }

  if (!terms.value.service_terms_agreed) {
    setFieldError('service_terms_agreed', '서비스 이용약관에 동의해야 합니다.')
    valid = false
  }

  if (!terms.value.privacy_agreed) {
    setFieldError('privacy_agreed', '개인정보 수집 및 이용에 동의해야 합니다.')
    valid = false
  }

  if (!regions.value.length) {
    setFieldError('region_ids', '지역을 최소 1개 선택해 주세요.')
    valid = false
  }

  if (!valid) {
    formErrors.value = ['입력 내용을 확인해 주세요.']
  }

  return valid
}

function buildPayload() {
  return {
    username: form.username.trim(),
    password: form.password,
    password_confirm: form.password_confirm,
    email: form.email.trim(),
    real_name: form.real_name.trim(),
    nickname: form.nickname.trim(),
    phone: form.phone.trim(),
    birth_date: form.birth_date || null,
    gender: form.gender || 'N',
    service_terms_agreed: terms.value.service_terms_agreed,
    privacy_agreed: terms.value.privacy_agreed,
    marketing_agreed: terms.value.marketing_agreed,
    region_ids: regions.value.map((region) => Number(region.region_id ?? region.id)),
  }
}

function applyApiErrors(error) {
  Object.assign(fieldErrors, error.fieldErrors || {})
  formErrors.value = error.formErrors?.length ? error.formErrors : [error.message || '회원가입에 실패했습니다.']
}

async function submitSignup() {
  clearErrors()
  if (!validateForm()) return

  isSubmitting.value = true

  try {
    await authStore.signupNormal(buildPayload())
    router.push('/mypage')
  } catch (error) {
    applyApiErrors(error)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="page-view auth-view auth-view--wide">
    <section class="panel form-panel">
      <p class="eyebrow">Normal Signup</p>
      <h1>일반 회원가입</h1>

      <div v-if="formErrors.length" class="alert alert--error" role="alert">
        <p v-for="message in formErrors" :key="message">{{ message }}</p>
      </div>

      <form class="stack-form" @submit.prevent="submitSignup">
        <div class="form-grid">
          <div class="form-field">
            <label for="normal-username">아이디</label>
            <input id="normal-username" v-model="form.username" type="text" autocomplete="username" required />
            <FormFieldError :errors="fieldErrors.username" />
          </div>

          <div class="form-field">
            <label for="normal-email">이메일</label>
            <input id="normal-email" v-model="form.email" type="email" autocomplete="email" required />
            <FormFieldError :errors="fieldErrors.email" />
          </div>

          <div class="form-field">
            <label for="normal-password">비밀번호</label>
            <input id="normal-password" v-model="form.password" type="password" autocomplete="new-password" required />
            <FormFieldError :errors="fieldErrors.password" />
          </div>

          <div class="form-field">
            <label for="normal-password-confirm">비밀번호 확인</label>
            <input
              id="normal-password-confirm"
              v-model="form.password_confirm"
              type="password"
              autocomplete="new-password"
              required
            />
            <FormFieldError :errors="fieldErrors.password_confirm" />
          </div>

          <div class="form-field">
            <label for="normal-real-name">실명</label>
            <input id="normal-real-name" v-model="form.real_name" type="text" autocomplete="name" required />
            <FormFieldError :errors="fieldErrors.real_name" />
          </div>

          <div class="form-field">
            <label for="normal-nickname">닉네임</label>
            <input id="normal-nickname" v-model="form.nickname" type="text" required />
            <FormFieldError :errors="fieldErrors.nickname" />
          </div>

          <div class="form-field">
            <label for="normal-phone">전화번호</label>
            <input id="normal-phone" v-model="form.phone" type="tel" autocomplete="tel" required />
            <FormFieldError :errors="fieldErrors.phone" />
          </div>

          <div class="form-field">
            <label for="normal-birth-date">생년월일</label>
            <input id="normal-birth-date" v-model="form.birth_date" type="date" />
            <FormFieldError :errors="fieldErrors.birth_date" />
          </div>

          <div class="form-field form-field--full">
            <label for="normal-gender">성별</label>
            <select id="normal-gender" v-model="form.gender">
              <option value="N">선택 안 함</option>
              <option value="M">남성</option>
              <option value="F">여성</option>
            </select>
            <FormFieldError :errors="fieldErrors.gender" />
          </div>
        </div>

        <TermsAgreement v-model="terms" :errors="fieldErrors" />
        <UserRegionFields v-model="regions" :errors="fieldErrors.region_ids" />

        <div class="form-actions">
          <button class="button button--primary" type="submit" :disabled="isSubmitting || authStore.isLoading">
            {{ isSubmitting ? '가입 중' : '가입하기' }}
          </button>
          <RouterLink to="/signup">유형 다시 선택</RouterLink>
        </div>
      </form>
    </section>
  </main>
</template>
