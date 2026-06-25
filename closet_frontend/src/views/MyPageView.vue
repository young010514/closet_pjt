<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { getMyRegions, normalizeApiError, updateMyRegions, updateMyProfile, updateMyBusinessProfile } from '@/api/accounts'
import { getMyApplications } from '@/api/community'
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

const myApplications = ref([])
const isLoadingApplications = ref(false)

const isEditingProfile = ref(false)
const isSavingProfile = ref(false)
const editForm = ref({})
const editErrors = ref({})
const editFormError = ref('')

function startEditingProfile() {
  const p = profile.value || {}
  editForm.value = {
    real_name: p.real_name || '',
    nickname: p.nickname || '',
    phone: p.phone || '',
    birth_date: p.birth_date || '',
    gender: p.gender || 'N',
  }
  editErrors.value = {}
  editFormError.value = ''
  isEditingProfile.value = true
}

function cancelEditingProfile() {
  isEditingProfile.value = false
}

const isEditingBusiness = ref(false)
const isSavingBusiness = ref(false)
const editBusinessForm = ref({})
const editBusinessErrors = ref({})
const editBusinessFormError = ref('')

function startEditingBusiness() {
  const bp = businessProfile.value || {}
  editBusinessForm.value = {
    business_contact_email: bp.business_contact_email || '',
    business_name: bp.business_name || '',
    business_number: bp.business_number || '',
    business_phone: bp.business_phone || '',
    owner_name: bp.owner_name || '',
    address: bp.address || '',
  }
  editBusinessErrors.value = {}
  editBusinessFormError.value = ''
  isEditingBusiness.value = true
}

function cancelEditingBusiness() {
  isEditingBusiness.value = false
}

async function saveBusinessProfile() {
  if (isSavingBusiness.value) return
  editBusinessErrors.value = {}
  editBusinessFormError.value = ''
  isSavingBusiness.value = true

  try {
    const data = await updateMyBusinessProfile(editBusinessForm.value)
    authStore.user = data
    isEditingBusiness.value = false
  } catch (error) {
    const normalized = normalizeApiError(error)
    editBusinessErrors.value = normalized.fieldErrors
    editBusinessFormError.value = normalized.message
  } finally {
    isSavingBusiness.value = false
  }
}

async function saveProfile() {
  if (isSavingProfile.value) return
  editErrors.value = {}
  editFormError.value = ''
  isSavingProfile.value = true

  try {
    const payload = { ...editForm.value }
    if (!payload.birth_date) payload.birth_date = null
    const data = await updateMyProfile(payload)
    authStore.user = data
    isEditingProfile.value = false
  } catch (error) {
    const normalized = normalizeApiError(error)
    editErrors.value = normalized.fieldErrors
    editFormError.value = normalized.message
  } finally {
    isSavingProfile.value = false
  }
}

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

function applicationStatusLabel(s) {
  if (s === 'approved') return '승인'
  if (s === 'rejected') return '거절'
  return '검토 중'
}

async function loadApplications() {
  if (!authStore.isAuthenticated || authStore.user?.profile?.user_type !== 'normal') return
  isLoadingApplications.value = true
  try {
    const res = await getMyApplications()
    myApplications.value = res.data
  } catch {
    // 조회 실패 시 빈 목록 유지
  } finally {
    isLoadingApplications.value = false
  }
}

onMounted(() => {
  loadRegions()
  loadApplications()
})
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
          <div class="section-header-row">
            <h2>프로필</h2>
            <button v-if="!isEditingProfile" class="button button--secondary button--sm" type="button" @click="startEditingProfile">
              수정
            </button>
          </div>

          <template v-if="!isEditingProfile">
            <dl class="info-list">
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
          </template>

          <template v-else>
            <form class="edit-form" @submit.prevent="saveProfile">
              <div class="edit-field">
                <label for="edit-real-name">실명</label>
                <input id="edit-real-name" v-model="editForm.real_name" type="text" maxlength="30" />
                <p v-if="editErrors.real_name" class="field-error">{{ editErrors.real_name[0] }}</p>
              </div>
              <div class="edit-field">
                <label for="edit-nickname">닉네임</label>
                <input id="edit-nickname" v-model="editForm.nickname" type="text" maxlength="30" />
                <p v-if="editErrors.nickname" class="field-error">{{ editErrors.nickname[0] }}</p>
              </div>
              <div class="edit-field">
                <label for="edit-phone">전화번호</label>
                <input id="edit-phone" v-model="editForm.phone" type="tel" maxlength="20" />
                <p v-if="editErrors.phone" class="field-error">{{ editErrors.phone[0] }}</p>
              </div>
              <div class="edit-field">
                <label for="edit-birth-date">생년월일</label>
                <input id="edit-birth-date" v-model="editForm.birth_date" type="date" />
                <p v-if="editErrors.birth_date" class="field-error">{{ editErrors.birth_date[0] }}</p>
              </div>
              <div class="edit-field">
                <label for="edit-gender">성별</label>
                <select id="edit-gender" v-model="editForm.gender">
                  <option value="N">선택 안 함</option>
                  <option value="M">남성</option>
                  <option value="F">여성</option>
                </select>
                <p v-if="editErrors.gender" class="field-error">{{ editErrors.gender[0] }}</p>
              </div>

              <p v-if="editFormError" class="alert alert--error">{{ editFormError }}</p>

              <div class="form-actions form-actions--compact">
                <button class="button button--primary" type="submit" :disabled="isSavingProfile">
                  {{ isSavingProfile ? '저장 중' : '저장하기' }}
                </button>
                <button class="button button--secondary" type="button" :disabled="isSavingProfile" @click="cancelEditingProfile">
                  취소
                </button>
              </div>
            </form>
          </template>
        </section>

        <section v-if="businessProfile" class="info-section">
          <div class="section-header-row">
            <h2>사업자 정보</h2>
            <button v-if="!isEditingBusiness" class="button button--secondary button--sm" type="button" @click="startEditingBusiness">
              수정
            </button>
          </div>

          <template v-if="!isEditingBusiness">
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
          </template>

          <template v-else>
            <form class="edit-form" @submit.prevent="saveBusinessProfile">
              <div class="edit-field">
                <label for="edit-biz-email">공개 연락 이메일</label>
                <input id="edit-biz-email" v-model="editBusinessForm.business_contact_email" type="email" />
                <p v-if="editBusinessErrors.business_contact_email" class="field-error">{{ editBusinessErrors.business_contact_email[0] }}</p>
              </div>
              <div class="edit-field">
                <label for="edit-biz-name">상호명</label>
                <input id="edit-biz-name" v-model="editBusinessForm.business_name" type="text" maxlength="100" />
                <p v-if="editBusinessErrors.business_name" class="field-error">{{ editBusinessErrors.business_name[0] }}</p>
              </div>
              <div class="edit-field">
                <label for="edit-biz-number">사업자등록번호</label>
                <input id="edit-biz-number" v-model="editBusinessForm.business_number" type="text" maxlength="30" />
                <p v-if="editBusinessErrors.business_number" class="field-error">{{ editBusinessErrors.business_number[0] }}</p>
              </div>
              <div class="edit-field">
                <label for="edit-biz-phone">사업자 전화번호</label>
                <input id="edit-biz-phone" v-model="editBusinessForm.business_phone" type="tel" maxlength="20" />
                <p v-if="editBusinessErrors.business_phone" class="field-error">{{ editBusinessErrors.business_phone[0] }}</p>
              </div>
              <div class="edit-field">
                <label for="edit-biz-owner">대표자명</label>
                <input id="edit-biz-owner" v-model="editBusinessForm.owner_name" type="text" maxlength="30" />
                <p v-if="editBusinessErrors.owner_name" class="field-error">{{ editBusinessErrors.owner_name[0] }}</p>
              </div>
              <div class="edit-field">
                <label for="edit-biz-address">사업장 주소</label>
                <input id="edit-biz-address" v-model="editBusinessForm.address" type="text" maxlength="255" />
                <p v-if="editBusinessErrors.address" class="field-error">{{ editBusinessErrors.address[0] }}</p>
              </div>

              <p v-if="editBusinessFormError" class="alert alert--error">{{ editBusinessFormError }}</p>

              <div class="form-actions form-actions--compact">
                <button class="button button--primary" type="submit" :disabled="isSavingBusiness">
                  {{ isSavingBusiness ? '저장 중' : '저장하기' }}
                </button>
                <button class="button button--secondary" type="button" :disabled="isSavingBusiness" @click="cancelEditingBusiness">
                  취소
                </button>
              </div>
            </form>
          </template>
        </section>

        <section v-if="profile?.user_type === 'normal'" class="info-section">
          <h2>내 체험단 신청 내역</h2>
          <p v-if="isLoadingApplications" class="muted-text">불러오는 중...</p>
          <p v-else-if="myApplications.length === 0" class="muted-text">신청한 체험단이 없습니다.</p>
          <table v-else class="mypage-applications">
            <thead>
              <tr>
                <th>체험단</th>
                <th>신청 상태</th>
                <th>거절 사유</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="app in myApplications" :key="app.id">
                <td>
                  <RouterLink :to="{ name: 'community-detail', params: { pk: app.post_id } }">
                    {{ app.post_title }}
                  </RouterLink>
                </td>
                <td>
                  <span :class="['mypage-badge', `mypage-badge--${app.status}`]">
                    {{ applicationStatusLabel(app.status) }}
                  </span>
                </td>
                <td class="mypage-reject-reason">{{ app.rejection_reason || '-' }}</td>
              </tr>
            </tbody>
          </table>
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

<style scoped>
.mypage-applications {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  margin-top: 8px;
}
.mypage-applications th,
.mypage-applications td {
  padding: 8px 12px;
  border-bottom: 1px solid #eee;
  text-align: left;
  vertical-align: top;
}
.mypage-applications th {
  background: #f5f5f5;
  font-weight: 600;
}
.mypage-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
}
.mypage-badge--pending { background: #f0f0f0; color: #555; }
.mypage-badge--approved { background: #d4edda; color: #155724; }
.mypage-badge--rejected { background: #f8d7da; color: #721c24; }
.mypage-reject-reason {
  color: #721c24;
  font-size: 0.85rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.section-header-row h2 {
  margin: 0;
}

.button--sm {
  padding: 0.3rem 0.8rem;
  font-size: 0.85rem;
}

.edit-form {
  display: grid;
  gap: 0.9rem;
}

.edit-field {
  display: grid;
  gap: 0.3rem;
}

.edit-field label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-muted);
}

.edit-field input,
.edit-field select {
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 0.95rem;
  background: #fff;
  width: 100%;
  box-sizing: border-box;
}

.edit-field input:focus,
.edit-field select:focus {
  outline: none;
  border-color: var(--color-accent);
}

.field-error {
  margin: 0;
  color: #c0392b;
  font-size: 0.82rem;
}
</style>
