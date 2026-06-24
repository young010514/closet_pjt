<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { getMyRegions, normalizeApiError, updateMyRegions } from '@/api/accounts'
import RegionSelector from '@/components/RegionSelector.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const regions = ref([])
const savedRegionIds = ref([])
const regionErrors = ref([])
const regionMessage = ref('')
const regionMessageError = ref(false)
const isLoadingRegions = ref(false)
const isSavingRegions = ref(false)

const user = computed(() => authStore.user)
const profile = computed(() => user.value?.profile || null)
const businessProfile = computed(() => user.value?.business_profile || null)
const regionIds = computed(() =>
  regions.value.map((region) => Number(region.region_id ?? region.id)).filter(Boolean),
)
const hasRegionChanges = computed(
  () => regionIds.value.join(',') !== savedRegionIds.value.join(','),
)

function displayValue(value) {
  return value || '-'
}

function formatUserType(value) {
  if (value === 'normal') return '일반 회원'
  if (value === 'business') return '사업자 회원'
  return '미지정'
}

function formatGender(value) {
  if (value === 'M') return '남성'
  if (value === 'F') return '여성'
  return '선택 안 함'
}

async function loadRegions() {
  if (!authStore.isAuthenticated) return

  isLoadingRegions.value = true
  regionErrors.value = []
  regionMessage.value = ''
  regionMessageError.value = false

  try {
    const data = await getMyRegions()
    regions.value = Array.isArray(data.regions) ? data.regions : []
    savedRegionIds.value = regionIds.value
  } catch (error) {
    const normalized = normalizeApiError(error)
    if ([401, 403].includes(normalized.status)) {
      router.push('/login')
      return
    }

    regionMessageError.value = true
    regionMessage.value = normalized.message
  } finally {
    isLoadingRegions.value = false
  }
}

async function saveRegions() {
  if (!hasRegionChanges.value || isSavingRegions.value) return

  regionErrors.value = []
  regionMessage.value = ''
  regionMessageError.value = false
  isSavingRegions.value = true

  try {
    const data = await updateMyRegions(regionIds.value)
    regions.value = Array.isArray(data.regions) ? data.regions : []
    savedRegionIds.value = regionIds.value
    try {
      await authStore.fetchCurrentUser()
    } catch (error) {
      console.warn('Failed to refresh current user after saving regions.', error)
    }
    regionMessage.value = '지역이 저장되었습니다.'
  } catch (error) {
    const normalized = normalizeApiError(error)
    regionErrors.value =
      normalized.fieldErrors.region_ids ||
      normalized.formErrors ||
      [normalized.message]
    regionMessageError.value = true
    regionMessage.value = normalized.message
  } finally {
    isSavingRegions.value = false
  }
}

async function logout() {
  if (!window.confirm('로그아웃 하시겠습니까?')) return

  await authStore.logout()
  router.push('/login')
}

onMounted(loadRegions)
</script>

<template>
  <main class="page-view">
    <section class="panel profile-panel">
      <div class="page-header-row">
        <div>
          <p class="eyebrow">My Page</p>
          <h1>마이페이지</h1>
        </div>
        <div class="form-actions">
          <RouterLink
            v-if="user"
            class="button button--secondary"
            :to="{ name: 'user-profile', params: { userId: user.id } }"
          >
            공개 프로필 보기
          </RouterLink>
          <button class="button button--secondary" type="button" :disabled="authStore.isLoading" @click="logout">
            로그아웃
          </button>
        </div>
      </div>

      <div v-if="!user" class="alert alert--info">사용자 정보를 불러오는 중입니다.</div>

      <template v-else>
        <section class="info-section">
          <h2>계정 정보</h2>
          <dl class="info-list">
            <div>
              <dt>사용자 ID</dt>
              <dd>{{ user.id }}</dd>
            </div>
            <div>
              <dt>아이디</dt>
              <dd>{{ displayValue(user.username) }}</dd>
            </div>
            <div>
              <dt>이메일</dt>
              <dd>{{ displayValue(user.email) }}</dd>
            </div>
          </dl>
        </section>

        <section class="info-section">
          <h2>프로필</h2>
          <dl class="info-list">
            <div>
              <dt>회원 유형</dt>
              <dd>{{ formatUserType(profile?.user_type) }}</dd>
            </div>
            <div>
              <dt>실명</dt>
              <dd>{{ displayValue(profile?.real_name) }}</dd>
            </div>
            <div>
              <dt>닉네임</dt>
              <dd>{{ displayValue(profile?.nickname) }}</dd>
            </div>
            <div>
              <dt>전화번호</dt>
              <dd>{{ displayValue(profile?.phone) }}</dd>
            </div>
            <div>
              <dt>생년월일</dt>
              <dd>{{ displayValue(profile?.birth_date) }}</dd>
            </div>
            <div>
              <dt>성별</dt>
              <dd>{{ formatGender(profile?.gender) }}</dd>
            </div>
          </dl>
        </section>

        <section v-if="businessProfile" class="info-section">
          <h2>사업자 정보</h2>
          <dl class="info-list">
            <div>
              <dt>공개 연락 이메일</dt>
              <dd>{{ displayValue(businessProfile.business_contact_email) }}</dd>
            </div>
            <div>
              <dt>상호명</dt>
              <dd>{{ displayValue(businessProfile.business_name) }}</dd>
            </div>
            <div>
              <dt>사업자등록번호</dt>
              <dd>{{ displayValue(businessProfile.business_number) }}</dd>
            </div>
            <div>
              <dt>사업자 전화번호</dt>
              <dd>{{ displayValue(businessProfile.business_phone) }}</dd>
            </div>
            <div>
              <dt>대표자명</dt>
              <dd>{{ displayValue(businessProfile.owner_name) }}</dd>
            </div>
            <div>
              <dt>사업장 주소</dt>
              <dd>{{ displayValue(businessProfile.address) }}</dd>
            </div>
          </dl>
        </section>

        <section class="info-section">
          <p v-if="isLoadingRegions" class="muted-text">지역 정보를 불러오는 중입니다.</p>

          <RegionSelector
            v-else
            v-model="regions"
            :errors="regionErrors"
          />

          <div class="form-actions form-actions--compact">
            <button
              class="button button--primary"
              type="button"
              :disabled="!hasRegionChanges || isSavingRegions || isLoadingRegions"
              @click="saveRegions"
            >
              {{ isSavingRegions ? '저장 중' : '저장하기' }}
            </button>
          </div>

          <p v-if="regionMessage" :class="['status-text', { 'status-text--error': regionMessageError }]">
            {{ regionMessage }}
          </p>
        </section>
      </template>
    </section>
  </main>
</template>
