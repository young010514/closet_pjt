<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { normalizeApiError, reorderRegions } from '@/api/accounts'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const regionRows = ref([])
const reorderMessage = ref('')
const reorderError = ref(false)
const isSavingOrder = ref(false)

const user = computed(() => authStore.user)
const profile = computed(() => user.value?.profile || null)
const businessProfile = computed(() => user.value?.business_profile || null)

watch(
  () => profile.value?.regions,
  (regions) => {
    regionRows.value = sortRegions(regions)
  },
  { immediate: true, deep: true },
)

const regionIds = computed(() => regionRows.value.map(regionPrimaryId).filter(Boolean))
const savedRegionIds = computed(() => sortRegions(profile.value?.regions).map(regionPrimaryId).filter(Boolean))
const canReorder = computed(() => regionRows.value.length >= 2)
const hasOrderChanged = computed(() => regionIds.value.join(',') !== savedRegionIds.value.join(','))

function sortRegions(regions = []) {
  return [...(regions || [])].sort((left, right) => (left.priority || 0) - (right.priority || 0))
}

function regionPrimaryId(item) {
  return item?.region?.id ?? item?.region_id ?? null
}

function regionLabel(item) {
  const region = item?.region
  if (!region) return '지역 정보 없음'
  return region.full_name || [region.sido, region.sigungu, region.dong].filter(Boolean).join(' ') || `지역 ${region.id}`
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

function displayValue(value) {
  return value || '-'
}

function moveRegion(from, to) {
  if (to < 0 || to >= regionRows.value.length) return
  reorderMessage.value = ''
  const next = [...regionRows.value]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  regionRows.value = next
}

async function saveRegionOrder() {
  if (!canReorder.value || !hasOrderChanged.value) return

  reorderMessage.value = ''
  reorderError.value = false
  isSavingOrder.value = true

  try {
    await reorderRegions(regionIds.value)
    await authStore.fetchCurrentUser()
    reorderMessage.value = '지역 순서가 변경되었습니다.'
  } catch (error) {
    const normalized = error?.fieldErrors ? error : normalizeApiError(error)
    reorderError.value = true
    reorderMessage.value = normalized.message || '지역 순서를 변경하지 못했습니다.'
    regionRows.value = sortRegions(profile.value?.regions)
  } finally {
    isSavingOrder.value = false
  }
}

async function logout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <main class="page-view">
    <section class="panel profile-panel">
      <div class="page-header-row">
        <div>
          <p class="eyebrow">My Page</p>
          <h1>마이페이지</h1>
        </div>
        <button class="button button--secondary" type="button" :disabled="authStore.isLoading" @click="logout">
          로그아웃
        </button>
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
          <div class="section-heading">
            <h2>선택 지역</h2>
            <span>{{ regionRows.length }}개</span>
          </div>

          <p v-if="!regionRows.length" class="muted-text">등록된 지역이 없습니다.</p>

          <ul v-else class="selected-list">
            <li v-for="(item, index) in regionRows" :key="item.id || regionPrimaryId(item)" class="selected-item">
              <span>{{ index + 1 }}순위 · {{ regionLabel(item) }}</span>
              <span v-if="canReorder" class="button-group">
                <button type="button" class="mini-button" :disabled="index === 0" @click="moveRegion(index, index - 1)">
                  위로
                </button>
                <button
                  type="button"
                  class="mini-button"
                  :disabled="index === regionRows.length - 1"
                  @click="moveRegion(index, index + 1)"
                >
                  아래로
                </button>
              </span>
            </li>
          </ul>

          <div v-if="canReorder" class="form-actions form-actions--compact">
            <button
              class="button button--primary"
              type="button"
              :disabled="!hasOrderChanged || isSavingOrder"
              @click="saveRegionOrder"
            >
              {{ isSavingOrder ? '저장 중' : '순서 저장' }}
            </button>
          </div>

          <p v-if="reorderMessage" :class="['status-text', { 'status-text--error': reorderError }]">
            {{ reorderMessage }}
          </p>
        </section>
      </template>
    </section>
  </main>
</template>
