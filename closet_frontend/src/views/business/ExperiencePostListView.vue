<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { deleteExperiencePost, getExperiencePosts } from '@/api/business'

const router = useRouter()
const posts = ref([])
const isLoading = ref(false)
const errorMessage = ref('')

onMounted(loadPosts)

async function loadPosts() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    posts.value = await getExperiencePosts()
  } catch {
    errorMessage.value = '목록을 불러오지 못했습니다.'
  } finally {
    isLoading.value = false
  }
}

function statusLabel(status) {
  const map = { recruiting: '모집 중', closed: '모집 마감', ended: '체험 종료' }
  return map[status] || '-'
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('ko-KR')
}

async function handleDelete(pk) {
  if (!confirm('공고를 삭제하시겠습니까?')) return
  try {
    await deleteExperiencePost(pk)
    posts.value = posts.value.filter((p) => p.id !== pk)
  } catch {
    alert('삭제에 실패했습니다.')
  }
}
</script>

<template>
  <main class="exp-list">
    <div class="exp-list__header">
      <h1 class="exp-list__title">체험단 공고 관리</h1>
      <router-link :to="{ name: 'business-experience-new' }" class="exp-list__btn exp-list__btn--create">
        새 공고 등록
      </router-link>
    </div>

    <div v-if="isLoading" class="exp-list__status">불러오는 중...</div>
    <div v-else-if="errorMessage" class="exp-list__status exp-list__status--error">{{ errorMessage }}</div>
    <div v-else-if="posts.length === 0" class="exp-list__status">등록된 공고가 없습니다.</div>

    <table v-else class="exp-list__table">
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
        <tr v-for="post in posts" :key="post.id">
          <td>{{ post.title }}</td>
          <td>{{ formatDate(post.recruit_start) }} ~ {{ formatDate(post.recruit_end) }}</td>
          <td>{{ formatDate(post.experience_end) }}</td>
          <td>
            <span :class="['exp-list__badge', `exp-list__badge--${post.experience_status}`]">
              {{ statusLabel(post.experience_status) }}
            </span>
          </td>
          <td class="exp-list__actions">
            <router-link :to="{ name: 'business-experience-applicants', params: { pk: post.id } }" class="exp-list__btn exp-list__btn--view">
              신청자
            </router-link>
            <router-link :to="{ name: 'business-experience-edit', params: { pk: post.id } }" class="exp-list__btn exp-list__btn--edit">
              수정
            </router-link>
            <button class="exp-list__btn exp-list__btn--delete" @click="handleDelete(post.id)">삭제</button>
          </td>
        </tr>
      </tbody>
    </table>
  </main>
</template>

<style scoped>
.exp-list {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px 16px;
}
.exp-list__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.exp-list__title {
  font-size: 1.4rem;
  font-weight: 700;
}
.exp-list__status {
  padding: 20px;
  text-align: center;
  color: #666;
}
.exp-list__status--error { color: #c0392b; }
.exp-list__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.exp-list__table th,
.exp-list__table td {
  padding: 10px 12px;
  border-bottom: 1px solid #eee;
  text-align: left;
}
.exp-list__table th {
  background: #f5f5f5;
  font-weight: 600;
}
.exp-list__actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.exp-list__btn {
  padding: 5px 12px;
  border-radius: 4px;
  font-size: 0.85rem;
  cursor: pointer;
  border: none;
  text-decoration: none;
  display: inline-block;
}
.exp-list__btn--create { background: #3b82f6; color: #fff; }
.exp-list__btn--view { background: #10b981; color: #fff; }
.exp-list__btn--edit { background: #f59e0b; color: #fff; }
.exp-list__btn--delete { background: #ef4444; color: #fff; }
.exp-list__badge {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  white-space: nowrap;
}
.exp-list__badge--recruiting { background: #dcfce7; color: #166534; }
.exp-list__badge--closed { background: #fef3c7; color: #92400e; }
.exp-list__badge--ended { background: #f3f4f6; color: #374151; }
</style>
