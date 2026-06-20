<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { getSignupTypes, normalizeApiError } from '@/api/accounts'

const fallbackTypes = [
  { type: 'normal', label: '일반 회원', endpoint: '/api/accounts/signup/normal/' },
  { type: 'business', label: '사업자 회원', endpoint: '/api/accounts/signup/business/' },
]

const typeLabels = {
  normal: '일반 회원',
  business: '사업자 회원',
}

const signupTypes = ref(fallbackTypes)
const isLoading = ref(false)
const message = ref('')

const cards = computed(() =>
  signupTypes.value.map((item) => ({
    ...item,
    displayLabel: typeLabels[item.type] || item.label || item.type,
    route: item.type === 'business' ? '/signup/business' : '/signup/normal',
  })),
)

onMounted(async () => {
  isLoading.value = true
  message.value = ''

  try {
    const data = await getSignupTypes()
    if (Array.isArray(data.signup_types) && data.signup_types.length) {
      signupTypes.value = data.signup_types
    }
  } catch (error) {
    const normalized = normalizeApiError(error)
    message.value = `${normalized.message} 기본 선택지를 표시합니다.`
    signupTypes.value = fallbackTypes
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <main class="page-view">
    <section class="panel">
      <p class="eyebrow">Signup</p>
      <h1>회원가입 유형 선택</h1>
      <p class="lead-text">사용할 계정 유형을 선택해 주세요.</p>

      <div v-if="message" class="alert alert--info" role="status">{{ message }}</div>
      <p v-if="isLoading" class="muted-text">회원가입 유형을 불러오는 중입니다.</p>

      <div class="choice-grid">
        <RouterLink v-for="item in cards" :key="item.type" class="choice-card" :to="item.route">
          <span>{{ item.displayLabel }}</span>
          <small>{{ item.endpoint }}</small>
        </RouterLink>
      </div>
    </section>
  </main>
</template>
