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
  business_contact_email: '',
  password: '',
  password_confirm: '',
  nickname: '',
  business_name: '',
  business_number: '',
  business_phone: '',
  owner_name: '',
  birth_date: '',
  address: '',
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
    ['email', '계정 이메일'],
    ['password', '비밀번호'],
    ['password_confirm', '비밀번호 확인'],
    ['nickname', '커뮤니티 닉네임'],
    ['business_name', '상호명'],
    ['business_number', '사업자등록번호'],
    ['business_phone', '사업자 전화번호'],
    ['owner_name', '대표자명'],
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
    business_contact_email: form.business_contact_email.trim(),
    nickname: form.nickname.trim(),
    business_name: form.business_name.trim(),
    business_number: form.business_number.trim(),
    business_phone: form.business_phone.trim(),
    owner_name: form.owner_name.trim(),
    birth_date: form.birth_date || null,
    address: form.address.trim(),
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
    await authStore.signupBusiness(buildPayload())
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
      <p class="eyebrow">Business Signup</p>
      <h1>사업자 회원가입</h1>
      <RouterLink to="/signup/normal">일반사용자로 회원가입 하시겠습니까?</RouterLink>

      <div v-if="formErrors.length" class="alert alert--error" role="alert">
        <p v-for="message in formErrors" :key="message">{{ message }}</p>
      </div>

      <form class="stack-form" @submit.prevent="submitSignup">
        <div class="form-grid">
          <div class="form-field">
            <label for="business-username">아이디</label>
            <input id="business-username" v-model="form.username" type="text" autocomplete="username" required />
            <FormFieldError :errors="fieldErrors.username" />
          </div>

          <div class="form-field">
            <label for="business-email">계정 이메일</label>
            <input id="business-email" v-model="form.email" type="email" autocomplete="email" required />
            <FormFieldError :errors="fieldErrors.email" />
          </div>

          <div class="form-field">
            <label for="business-contact-email">사업자 공개 연락 이메일</label>
            <input id="business-contact-email" v-model="form.business_contact_email" type="email" />
            <FormFieldError :errors="fieldErrors.business_contact_email" />
          </div>

          <div class="form-field">
            <label for="business-nickname">커뮤니티 닉네임</label>
            <input id="business-nickname" v-model="form.nickname" type="text" required />
            <FormFieldError :errors="fieldErrors.nickname" />
          </div>

          <div class="form-field">
            <label for="business-password">비밀번호</label>
            <input id="business-password" v-model="form.password" type="password" autocomplete="new-password" required />
            <FormFieldError :errors="fieldErrors.password" />
          </div>

          <div class="form-field">
            <label for="business-password-confirm">비밀번호 확인</label>
            <input
              id="business-password-confirm"
              v-model="form.password_confirm"
              type="password"
              autocomplete="new-password"
              required
            />
            <FormFieldError :errors="fieldErrors.password_confirm" />
          </div>

          <div class="form-field">
            <label for="business-name">상호명</label>
            <input id="business-name" v-model="form.business_name" type="text" required />
            <FormFieldError :errors="fieldErrors.business_name" />
          </div>

          <div class="form-field">
            <label for="business-number">사업자등록번호</label>
            <input id="business-number" v-model="form.business_number" type="text" required />
            <FormFieldError :errors="fieldErrors.business_number" />
          </div>

          <div class="form-field">
            <label for="business-phone">사업자 전화번호</label>
            <input id="business-phone" v-model="form.business_phone" type="tel" required />
            <FormFieldError :errors="fieldErrors.business_phone" />
          </div>

          <div class="form-field">
            <label for="business-owner-name">대표자명</label>
            <input id="business-owner-name" v-model="form.owner_name" type="text" required />
            <FormFieldError :errors="fieldErrors.owner_name" />
          </div>

          <div class="form-field">
            <label for="business-birth-date">생년월일</label>
            <input id="business-birth-date" v-model="form.birth_date" type="date" />
            <FormFieldError :errors="fieldErrors.birth_date" />
          </div>

          <div class="form-field form-field--full">
            <label for="business-address">사업장 주소</label>
            <input id="business-address" v-model="form.address" type="text" />
            <FormFieldError :errors="fieldErrors.address" />
          </div>
        </div>

        <TermsAgreement v-model="terms" :errors="fieldErrors" />
        <UserRegionFields v-model="regions" :errors="fieldErrors.region_ids" />

        <div class="form-actions">
          <button class="button button--primary" type="submit" :disabled="isSubmitting || authStore.isLoading">
            {{ isSubmitting ? '가입 중' : '가입하기' }}
          </button>
        </div>
      </form>
    </section>
  </main>
</template>
