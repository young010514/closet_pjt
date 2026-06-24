<script setup>
import { onMounted, ref } from 'vue'
import {
  deleteExperiencePost,
  deleteStorePost,
  getDashboard,
  getExperiencePosts,
  getStorePosts,
} from '@/api/business'

const activeTab = ref('overview')

// 개요
const dashboard = ref(null)
const overviewLoading = ref(false)
const overviewError = ref('')

// 가게 관리
const storePosts = ref([])
const storeLoading = ref(false)
const storeLoaded = ref(false)
const storeOrdering = ref('latest')

// 체험단 관리
const expPosts = ref([])
const expLoading = ref(false)
const expLoaded = ref(false)

onMounted(loadOverview)

async function loadOverview() {
  overviewLoading.value = true
  overviewError.value = ''
  try {
    dashboard.value = await getDashboard()
  } catch {
    overviewError.value = '데이터를 불러오지 못했습니다.'
  } finally {
    overviewLoading.value = false
  }
}

async function switchTab(tab) {
  activeTab.value = tab
  if (tab === 'store' && !storeLoaded.value) {
    await loadStorePosts()
  } else if (tab === 'experience' && !expLoaded.value) {
    await loadExpPosts()
  }
}

async function loadStorePosts() {
  storeLoading.value = true
  try {
    storePosts.value = await getStorePosts(storeOrdering.value)
    storeLoaded.value = true
  } catch {
    // 빈 목록 유지
  } finally {
    storeLoading.value = false
  }
}

async function changeStoreOrdering(val) {
  storeOrdering.value = val
  storeLoaded.value = false
  await loadStorePosts()
}

async function handleStoreDelete(pk) {
  if (!confirm('게시글을 삭제하시겠습니까?')) return
  try {
    await deleteStorePost(pk)
    storePosts.value = storePosts.value.filter((p) => p.id !== pk)
  } catch {
    alert('삭제에 실패했습니다.')
  }
}

async function loadExpPosts() {
  expLoading.value = true
  try {
    expPosts.value = await getExperiencePosts()
    expLoaded.value = true
  } catch {
    // 빈 목록 유지
  } finally {
    expLoading.value = false
  }
}

async function handleExpDelete(pk) {
  if (!confirm('공고를 삭제하시겠습니까?')) return
  try {
    await deleteExperiencePost(pk)
    expPosts.value = expPosts.value.filter((p) => p.id !== pk)
  } catch {
    alert('삭제에 실패했습니다.')
  }
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('ko-KR')
}

function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function boardLabel(board) {
  const map = { fashion: '패션 정보 공유', daily: '일상 & 소통', local_shop: '우리 동네 가게', experience: '체험단' }
  return map[board] || board
}

function expStatusLabel(status) {
  const map = { recruiting: '모집 중', closed: '모집 마감', ended: '체험 종료' }
  return map[status] || '-'
}
</script>

<template>
  <main class="biz">
    <h1 class="biz__title">사업자 대시보드</h1>

    <!-- 탭 네비게이션 -->
    <nav class="biz__tabs">
      <button
        :class="['biz__tab', { 'biz__tab--active': activeTab === 'overview' }]"
        @click="switchTab('overview')"
      >
        개요
      </button>
      <button
        :class="['biz__tab', { 'biz__tab--active': activeTab === 'store' }]"
        @click="switchTab('store')"
      >
        가게 관리
      </button>
      <button
        :class="['biz__tab', { 'biz__tab--active': activeTab === 'experience' }]"
        @click="switchTab('experience')"
      >
        체험단 관리
      </button>
    </nav>

    <!-- 개요 탭 -->
    <section v-if="activeTab === 'overview'" class="biz__content">
      <div v-if="overviewLoading" class="biz__status">데이터를 불러오는 중...</div>
      <div v-else-if="overviewError" class="biz__status biz__status--error">{{ overviewError }}</div>
      <template v-else-if="dashboard">
        <!-- 가게 요약 -->
        <div class="biz__section">
          <h2 class="biz__section-title">가게 요약</h2>
          <div class="biz__card">
            <div class="biz__card-row">
              <span class="biz__label">상호명</span>
              <span class="biz__value">{{ dashboard.store_summary.store_name || '-' }}</span>
            </div>
            <div class="biz__card-row">
              <span class="biz__label">주소</span>
              <span class="biz__value">{{ dashboard.store_summary.store_address || '-' }}</span>
            </div>
          </div>
        </div>

        <!-- 체험단 현황 -->
        <div class="biz__section">
          <h2 class="biz__section-title">체험단 현황</h2>
          <div class="biz__stat-grid">
            <div class="biz__stat-card">
              <span class="biz__stat-label">모집 중</span>
              <span class="biz__stat-value">{{ dashboard.experience_summary.recruiting }}</span>
            </div>
            <div class="biz__stat-card">
              <span class="biz__stat-label">모집 마감</span>
              <span class="biz__stat-value">{{ dashboard.experience_summary.closed }}</span>
            </div>
            <div class="biz__stat-card">
              <span class="biz__stat-label">체험 종료</span>
              <span class="biz__stat-value">{{ dashboard.experience_summary.ended }}</span>
            </div>
            <div class="biz__stat-card biz__stat-card--total">
              <span class="biz__stat-label">전체</span>
              <span class="biz__stat-value">{{ dashboard.experience_summary.total }}</span>
            </div>
          </div>
        </div>

        <!-- 신청자 현황 -->
        <div class="biz__section">
          <h2 class="biz__section-title">체험단 신청자 현황</h2>
          <div v-if="dashboard.applicant_summary.length === 0" class="biz__empty">신청자 데이터가 없습니다.</div>
          <table v-else class="biz__table">
            <thead>
              <tr>
                <th>게시글 ID</th>
                <th>제목</th>
                <th>신청자 수</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in dashboard.applicant_summary" :key="item.post_id">
                <td>{{ item.post_id }}</td>
                <td>{{ item.title }}</td>
                <td>{{ item.applicant_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 최근 게시글 -->
        <div class="biz__section">
          <h2 class="biz__section-title">등록 게시글</h2>
          <div v-if="dashboard.recent_posts.length === 0" class="biz__empty">등록 게시글이 없습니다.</div>
          <ul v-else class="biz__post-list">
            <li v-for="post in dashboard.recent_posts" :key="post.id" class="biz__post-item">
              <span class="biz__post-title">{{ post.title }}</span>
              <span class="biz__post-board">{{ boardLabel(post.board) }}</span>
              <span class="biz__post-date">{{ formatDateTime(post.created_at) }}</span>
            </li>
          </ul>
        </div>
      </template>
    </section>

    <!-- 가게 관리 탭 -->
    <section v-else-if="activeTab === 'store'" class="biz__content">
      <div class="biz__section-header">
        <h2 class="biz__section-title">가게 관리</h2>
        <router-link :to="{ name: 'business-store-new' }" class="biz__btn biz__btn--primary">
          새 글 작성
        </router-link>
      </div>

      <div class="biz__ordering">
        <button
          v-for="(label, key) in { latest: '최신순', popular: '인기순', viewed: '조회순' }"
          :key="key"
          :class="['biz__order-btn', { active: storeOrdering === key }]"
          @click="changeStoreOrdering(key)"
        >
          {{ label }}
        </button>
      </div>

      <div v-if="storeLoading" class="biz__status">불러오는 중...</div>
      <div v-else-if="storePosts.length === 0" class="biz__empty">작성된 게시글이 없습니다.</div>
      <ul v-else class="biz__list">
        <li v-for="post in storePosts" :key="post.id" class="biz__list-item">
          <div class="biz__list-info">
            <span class="biz__list-title">{{ post.title }}</span>
            <span class="biz__list-date">{{ formatDate(post.created_at) }}</span>
          </div>
          <div class="biz__list-actions">
            <router-link :to="{ name: 'business-store-edit', params: { pk: post.id } }" class="biz__btn biz__btn--edit">
              수정
            </router-link>
            <button class="biz__btn biz__btn--delete" @click="handleStoreDelete(post.id)">삭제</button>
          </div>
        </li>
      </ul>
    </section>

    <!-- 체험단 관리 탭 -->
    <section v-else-if="activeTab === 'experience'" class="biz__content">
      <div class="biz__section-header">
        <h2 class="biz__section-title">체험단 관리</h2>
        <router-link :to="{ name: 'business-experience-new' }" class="biz__btn biz__btn--primary">
          새 공고 등록
        </router-link>
      </div>

      <div v-if="expLoading" class="biz__status">불러오는 중...</div>
      <div v-else-if="expPosts.length === 0" class="biz__empty">등록된 공고가 없습니다.</div>
      <table v-else class="biz__table">
        <thead>
          <tr>
            <th>제목</th>
            <th>모집 기간</th>
            <th>체험 종료</th>
            <th>상태</th>
            <th>관리</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="post in expPosts" :key="post.id">
            <td>{{ post.title }}</td>
            <td>{{ formatDate(post.recruit_start) }} ~ {{ formatDate(post.recruit_end) }}</td>
            <td>{{ formatDate(post.experience_end) }}</td>
            <td>
              <span :class="['biz__badge', `biz__badge--${post.experience_status}`]">
                {{ expStatusLabel(post.experience_status) }}
              </span>
            </td>
            <td class="biz__table-actions">
              <router-link :to="{ name: 'business-experience-applicants', params: { pk: post.id } }" class="biz__btn biz__btn--view">
                신청자
              </router-link>
              <router-link :to="{ name: 'business-experience-edit', params: { pk: post.id } }" class="biz__btn biz__btn--edit">
                수정
              </router-link>
              <button class="biz__btn biz__btn--delete" @click="handleExpDelete(post.id)">삭제</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>
</template>

<style scoped>
.biz {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px 16px;
}
.biz__title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 20px;
}
.biz__tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid #e0e0e0;
  margin-bottom: 24px;
}
.biz__tab {
  padding: 10px 24px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 0.95rem;
  color: #888;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color 0.15s, border-color 0.15s;
}
.biz__tab--active {
  color: #333;
  font-weight: 600;
  border-bottom-color: #333;
}
.biz__tab:hover:not(.biz__tab--active) {
  color: #555;
}
.biz__content {
  animation: fadeIn 0.15s ease;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.biz__section {
  margin-bottom: 32px;
}
.biz__section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.biz__section-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 2px solid #eee;
}
.biz__section-header .biz__section-title {
  margin-bottom: 0;
  border-bottom: none;
  padding-bottom: 0;
}
.biz__status {
  padding: 24px;
  text-align: center;
  color: #888;
}
.biz__status--error { color: #c0392b; }
.biz__empty {
  color: #999;
  padding: 20px 0;
}
.biz__card {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.biz__card-row {
  display: flex;
  gap: 12px;
}
.biz__label {
  color: #777;
  min-width: 200px;
}
.biz__value { font-weight: 500; }
.biz__stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.biz__stat-card {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.biz__stat-card--total {
  background: #f0f4ff;
  border-color: #aac4ff;
}
.biz__stat-label { font-size: 0.85rem; color: #666; }
.biz__stat-value { font-size: 1.5rem; font-weight: 700; }
.biz__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.biz__table th,
.biz__table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
  vertical-align: middle;
}
.biz__table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #444;
}
.biz__table tbody tr:hover { background: #fafafa; }
.biz__table-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.biz__post-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.biz__post-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fafafa;
}
.biz__post-title { flex: 1; font-weight: 500; }
.biz__post-board {
  font-size: 0.8rem;
  color: #fff;
  background: #666;
  border-radius: 4px;
  padding: 2px 8px;
  white-space: nowrap;
}
.biz__post-date { font-size: 0.85rem; color: #888; white-space: nowrap; }
.biz__ordering {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.biz__order-btn {
  padding: 6px 14px;
  border: 1px solid #ddd;
  border-radius: 20px;
  background: #fff;
  cursor: pointer;
  font-size: 0.85rem;
  color: #555;
}
.biz__order-btn.active {
  background: #333;
  color: #fff;
  border-color: #333;
}
.biz__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.biz__list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fafafa;
}
.biz__list-info { display: flex; flex-direction: column; gap: 4px; }
.biz__list-title { font-weight: 500; }
.biz__list-date { font-size: 0.8rem; color: #999; }
.biz__list-actions { display: flex; gap: 8px; }
.biz__btn {
  padding: 5px 12px;
  border-radius: 4px;
  font-size: 0.85rem;
  cursor: pointer;
  border: none;
  text-decoration: none;
  display: inline-block;
}
.biz__btn--primary { background: #333; color: #fff; padding: 8px 16px; }
.biz__btn--edit { background: #f59e0b; color: #fff; }
.biz__btn--delete { background: #ef4444; color: #fff; }
.biz__btn--view { background: #10b981; color: #fff; }
.biz__badge {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  white-space: nowrap;
}
.biz__badge--recruiting { background: #dcfce7; color: #166534; }
.biz__badge--closed { background: #fef3c7; color: #92400e; }
.biz__badge--ended { background: #f3f4f6; color: #374151; }
</style>
