<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStorePosts, deleteStorePost } from '@/api/business'

const router = useRouter()
const posts = ref([])
const ordering = ref('latest')
const isLoading = ref(false)
const errorMessage = ref('')

const ORDERING_LABELS = { latest: '최신순', popular: '인기순', viewed: '조회순' }

async function loadPosts() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    posts.value = await getStorePosts(ordering.value)
  } catch {
    errorMessage.value = '게시글을 불러오지 못했습니다.'
  } finally {
    isLoading.value = false
  }
}

async function handleDelete(pk) {
  if (!confirm('게시글을 삭제하시겠습니까?')) return
  try {
    await deleteStorePost(pk)
    posts.value = posts.value.filter((p) => p.id !== pk)
  } catch {
    alert('삭제에 실패했습니다.')
  }
}

function changeOrdering(val) {
  ordering.value = val
  loadPosts()
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('ko-KR')
}

onMounted(loadPosts)
</script>

<template>
  <main class="store-list">
    <div class="store-list__header">
      <h1 class="store-list__title">가게 관리</h1>
      <router-link :to="{ name: 'business-store-new' }" class="store-list__create-btn">
        새 글 작성
      </router-link>
    </div>

    <div class="store-list__ordering">
      <button
        v-for="(label, key) in ORDERING_LABELS"
        :key="key"
        :class="['store-list__order-btn', { active: ordering === key }]"
        @click="changeOrdering(key)"
      >
        {{ label }}
      </button>
    </div>

    <div v-if="isLoading" class="store-list__status">불러오는 중...</div>
    <div v-else-if="errorMessage" class="store-list__status store-list__status--error">
      {{ errorMessage }}
    </div>
    <div v-else-if="posts.length === 0" class="store-list__status">작성된 게시글이 없습니다.</div>

    <ul v-else class="store-list__items">
      <li v-for="post in posts" :key="post.id" class="store-list__item">
        <div class="store-list__item-info">
          <span class="store-list__item-title">{{ post.title }}</span>
          <span class="store-list__item-date">{{ formatDate(post.created_at) }}</span>
        </div>
        <div class="store-list__item-actions">
          <router-link
            :to="{ name: 'business-store-edit', params: { pk: post.id } }"
            class="store-list__action-btn"
          >
            수정
          </router-link>
          <button
            class="store-list__action-btn store-list__action-btn--delete"
            @click="handleDelete(post.id)"
          >
            삭제
          </button>
        </div>
      </li>
    </ul>
  </main>
</template>

<style scoped>
.store-list {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 16px;
}
.store-list__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.store-list__title {
  font-size: 1.4rem;
  font-weight: 700;
}
.store-list__create-btn {
  padding: 8px 16px;
  background: #333;
  color: #fff;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.9rem;
}
.store-list__ordering {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.store-list__order-btn {
  padding: 6px 14px;
  border: 1px solid #ddd;
  border-radius: 20px;
  background: #fff;
  cursor: pointer;
  font-size: 0.85rem;
  color: #555;
}
.store-list__order-btn.active {
  background: #333;
  color: #fff;
  border-color: #333;
}
.store-list__status {
  padding: 24px;
  text-align: center;
  color: #888;
}
.store-list__status--error {
  color: #c0392b;
}
.store-list__items {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.store-list__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fafafa;
}
.store-list__item-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.store-list__item-title {
  font-weight: 500;
}
.store-list__item-date {
  font-size: 0.8rem;
  color: #999;
}
.store-list__item-actions {
  display: flex;
  gap: 8px;
}
.store-list__action-btn {
  padding: 5px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 0.85rem;
  color: #555;
  text-decoration: none;
}
.store-list__action-btn--delete {
  color: #c0392b;
  border-color: #e8b4b4;
}
</style>
