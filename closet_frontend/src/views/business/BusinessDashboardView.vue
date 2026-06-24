<script setup>
import { onMounted, ref } from 'vue'

import { getDashboard } from '@/api/business'

const dashboard = ref(null)
const isLoading = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    dashboard.value = await getDashboard()
  } catch (err) {
    errorMessage.value =
      err?.response?.data?.detail || '대시보드 데이터를 불러오지 못했습니다.'
  } finally {
    isLoading.value = false
  }
})

function formatDate(value) {
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
  const map = {
    fashion: '패션 정보 공유',
    daily: '일상 & 소통',
    local_shop: '우리 동네 가게',
    experience: '체험단',
  }
  return map[board] || board
}
</script>

<template>
  <main class="dashboard">
    <h1 class="dashboard__title">사업자 대시보드</h1>

    <div v-if="isLoading" class="dashboard__status">데이터를 불러오는 중...</div>

    <div v-else-if="errorMessage" class="dashboard__status dashboard__status--error">
      {{ errorMessage }}
    </div>

    <template v-else-if="dashboard">
      <!-- 가게 요약 -->
      <section class="dashboard__section">
        <h2 class="dashboard__section-title">가게 요약</h2>
        <div class="dashboard__card">
          <div class="dashboard__card-row">
            <span class="dashboard__label">상호명</span>
            <span class="dashboard__value">{{ dashboard.store_summary.store_name || '-' }}</span>
          </div>
          <div class="dashboard__card-row">
            <span class="dashboard__label">우리 동네 가게 게시글 수</span>
            <span class="dashboard__value">{{ dashboard.store_summary.local_shop_post_count }}</span>
          </div>
        </div>
      </section>

      <!-- 체험단 현황 -->
      <section class="dashboard__section">
        <h2 class="dashboard__section-title">체험단 현황</h2>
        <div class="dashboard__stat-grid">
          <div class="dashboard__stat-card">
            <span class="dashboard__stat-label">모집 중</span>
            <span class="dashboard__stat-value">{{ dashboard.experience_summary.recruiting }}</span>
          </div>
          <div class="dashboard__stat-card">
            <span class="dashboard__stat-label">모집 마감</span>
            <span class="dashboard__stat-value">{{ dashboard.experience_summary.closed }}</span>
          </div>
          <div class="dashboard__stat-card">
            <span class="dashboard__stat-label">체험 종료</span>
            <span class="dashboard__stat-value">{{ dashboard.experience_summary.ended }}</span>
          </div>
          <div class="dashboard__stat-card dashboard__stat-card--total">
            <span class="dashboard__stat-label">전체</span>
            <span class="dashboard__stat-value">{{ dashboard.experience_summary.total }}</span>
          </div>
        </div>
      </section>

      <!-- 신청자 현황 -->
      <section class="dashboard__section">
        <h2 class="dashboard__section-title">신청자 현황</h2>
        <div v-if="dashboard.applicant_summary.length === 0" class="dashboard__empty">
          신청자 데이터가 없습니다.
        </div>
        <table v-else class="dashboard__table">
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
      </section>

      <!-- 최근 게시글 -->
      <section class="dashboard__section">
        <h2 class="dashboard__section-title">최근 게시글</h2>
        <div v-if="dashboard.recent_posts.length === 0" class="dashboard__empty">
          최근 게시글이 없습니다.
        </div>
        <ul v-else class="dashboard__post-list">
          <li
            v-for="post in dashboard.recent_posts"
            :key="post.id"
            class="dashboard__post-item"
          >
            <span class="dashboard__post-title">{{ post.title }}</span>
            <span class="dashboard__post-board">{{ boardLabel(post.board) }}</span>
            <span class="dashboard__post-date">{{ formatDate(post.created_at) }}</span>
          </li>
        </ul>
      </section>
    </template>
  </main>
</template>

<style scoped>
.dashboard {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 16px;
}

.dashboard__title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 24px;
}

.dashboard__status {
  padding: 16px;
  text-align: center;
  color: #555;
}

.dashboard__status--error {
  color: #c0392b;
}

.dashboard__section {
  margin-bottom: 32px;
}

.dashboard__section-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 2px solid #eee;
}

.dashboard__card {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dashboard__card-row {
  display: flex;
  gap: 12px;
}

.dashboard__label {
  color: #777;
  min-width: 180px;
}

.dashboard__value {
  font-weight: 500;
}

.dashboard__stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.dashboard__stat-card {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.dashboard__stat-card--total {
  background: #f0f4ff;
  border-color: #aac4ff;
}

.dashboard__stat-label {
  font-size: 0.85rem;
  color: #666;
}

.dashboard__stat-value {
  font-size: 1.5rem;
  font-weight: 700;
}

.dashboard__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
}

.dashboard__table th,
.dashboard__table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.dashboard__table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #444;
}

.dashboard__table tbody tr:hover {
  background: #fafafa;
}

.dashboard__empty {
  color: #999;
  padding: 16px 0;
}

.dashboard__post-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dashboard__post-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fafafa;
}

.dashboard__post-title {
  flex: 1;
  font-weight: 500;
}

.dashboard__post-board {
  font-size: 0.8rem;
  color: #fff;
  background: #666;
  border-radius: 4px;
  padding: 2px 8px;
  white-space: nowrap;
}

.dashboard__post-date {
  font-size: 0.85rem;
  color: #888;
  white-space: nowrap;
}
</style>
