<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCommunityStore } from '@/stores/community'

const route = useRoute()
const router = useRouter()
const store = useCommunityStore()
const authStore = useAuthStore()

const pk = Number(route.params.pk)

const BOARD_LABEL = {
  fashion: '패션 정보 공유',
  daily: '일상 & 소통',
  local_shop: '우리 동네 가게',
  experience: '체험단',
}

const CATEGORY_LABEL = {
  top: '상의', bottom: '하의', outer: '아우터', shoes: '슈즈',
  accessories: '잡화·악세사리', lifestyle: '라이프스타일',
  counseling: '고민·상담', recruit: '체험단 모집', review: '체험단 후기',
}

const EXPERIENCE_STATUS_LABEL = { recruiting: '모집중', closed: '마감', ended: '종료' }
const EXPERIENCE_STATUS_CLASS = {
  recruiting: 'status-recruiting',
  closed: 'status-closed',
  ended: 'status-ended',
}

const post = computed(() => store.currentPost)
const isRecruit = computed(() => post.value?.board === 'experience' && post.value?.category === 'recruit')
const isReview = computed(() => post.value?.board === 'experience' && post.value?.category === 'review')

onMounted(() => store.fetchPost(pk))

function goToList() {
  const board = post.value?.board ?? 'fashion'
  router.push({ path: '/community', query: { board } })
}

async function handleLike() {
  try { await store.likePost(pk) }
  catch { alert('좋아요 처리에 실패했습니다.') }
}

async function handleDelete() {
  if (!confirm('게시글을 삭제하시겠습니까?')) return
  const board = post.value?.board ?? 'fashion'
  try {
    await store.deletePost(pk)
    router.push({ path: '/community', query: { board } })
  } catch { alert('삭제에 실패했습니다.') }
}
</script>

<template>
  <div class="community-detail">
    <button class="btn-back" @click="goToList">← 목록</button>

    <p v-if="store.isLoading">불러오는 중...</p>
    <p v-else-if="store.error" class="error">{{ store.error }}</p>

    <article v-else-if="post">
      <!-- 배지 -->
      <div class="badges">
        <span class="badge board-badge">{{ BOARD_LABEL[post.board] ?? post.board }}</span>
        <span v-if="post.category" class="badge">{{ CATEGORY_LABEL[post.category] ?? post.category }}</span>
        <span v-if="post.gender" class="badge">{{ post.gender }}</span>
        <span
          v-if="post.experience_status"
          class="badge status-badge"
          :class="EXPERIENCE_STATUS_CLASS[post.experience_status]"
        >{{ EXPERIENCE_STATUS_LABEL[post.experience_status] }}</span>
      </div>

      <h1>{{ post.title }}</h1>

      <!-- 체험단 모집 정보 박스 -->
      <div v-if="isRecruit" class="info-box">
        <div class="info-row"><span class="info-label">가게 상호명</span><span>{{ post.store_name }}</span></div>
        <div class="info-row"><span class="info-label">가게 위치</span><span>{{ post.store_location }}</span></div>
        <div class="info-row">
          <span class="info-label">모집 기간</span>
          <span>{{ post.recruit_start }} ~ {{ post.recruit_end }}</span>
        </div>
        <div class="info-row"><span class="info-label">체험단 종료</span><span>{{ post.experience_end }}</span></div>
      </div>

      <!-- 체험단 후기 정보 박스 -->
      <div v-if="isReview" class="info-box">
        <div class="info-row"><span class="info-label">가게 상호명</span><span>{{ post.store_name }}</span></div>
        <div v-if="post.experience_participation_start" class="info-row">
          <span class="info-label">체험 기간</span>
          <span>{{ post.experience_participation_start }} ~ {{ post.experience_participation_end }}</span>
        </div>
      </div>

      <div class="meta">
        <span>{{ post.author_name }}</span>
        <span>조회 {{ post.view_count }}</span>
        <span>{{ new Date(post.created_at).toLocaleDateString() }}</span>
      </div>

      <!-- 이미지 갤러리 -->
      <div v-if="post.images?.length" class="image-gallery">
        <img v-for="img in post.images" :key="img.id" :src="img.image_url" alt="이미지" />
      </div>

      <!-- 체험단 모집: 상품 설명 + 공지사항 -->
      <template v-if="isRecruit">
        <div class="section">
          <h3>상품 설명</h3>
          <div class="post-content">{{ post.product_description }}</div>
        </div>
        <div class="section">
          <h3>공지 사항</h3>
          <div class="post-content notice-box">{{ post.notice }}</div>
        </div>
      </template>

      <!-- 체험단 후기 / 일반 게시판: content -->
      <template v-else>
        <div v-if="post.hashtags?.length" class="hashtags">
          <span v-for="tag in post.hashtags" :key="tag" class="tag">{{ tag }}</span>
        </div>
        <div class="post-content">{{ post.content }}</div>
      </template>

      <div class="actions">
        <button class="btn-like" @click="handleLike">♥ 좋아요 {{ post.like_count }}</button>
        <template v-if="authStore.isAuthenticated">
          <button class="btn-edit" @click="router.push(`/community/${pk}/edit`)">수정</button>
          <button class="btn-delete" @click="handleDelete">삭제</button>
        </template>
      </div>
    </article>
  </div>
</template>

<style scoped>
.community-detail { max-width: 800px; margin: 0 auto; padding: 1rem; }
.btn-back { background: none; border: none; cursor: pointer; color: #555; margin-bottom: 1rem; font-size: 0.9rem; }
.badges { display: flex; gap: 0.4rem; margin-bottom: 0.6rem; flex-wrap: wrap; align-items: center; }
.badge { font-size: 0.75rem; padding: 0.1rem 0.4rem; background: #eee; border-radius: 3px; }
.board-badge { background: #e8f0fe; color: #3c5fbe; }
.status-badge { font-weight: 600; }
.status-recruiting { background: #e6f4ea; color: #1e7e34; }
.status-closed { background: #fff3cd; color: #856404; }
.status-ended { background: #f8d7da; color: #721c24; }
h1 { font-size: 1.4rem; margin-bottom: 0.75rem; }

.info-box {
  background: #f8f9fa; border: 1px solid #eee; border-radius: 8px;
  padding: 0.9rem 1.1rem; margin-bottom: 0.75rem;
  display: flex; flex-direction: column; gap: 0.4rem;
}
.info-row { display: flex; gap: 1rem; font-size: 0.88rem; }
.info-label { color: #888; min-width: 90px; flex-shrink: 0; }

.meta { display: flex; gap: 1rem; font-size: 0.8rem; color: #888; margin-bottom: 1rem; }

.image-gallery {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.5rem; margin: 1rem 0;
}
.image-gallery img {
  width: 100%; aspect-ratio: 4/3; object-fit: cover;
  border-radius: 6px; border: 1px solid #eee;
}

.section { margin: 1.2rem 0; }
.section h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; border-bottom: 1px solid #eee; padding-bottom: 0.3rem; }
.post-content { white-space: pre-wrap; line-height: 1.7; }
.notice-box { background: #f8f9fa; border-radius: 6px; padding: 0.8rem 1rem; border: 1px solid #eee; }

.hashtags { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
.tag { font-size: 0.8rem; color: #5b8af0; }

.actions { display: flex; gap: 0.5rem; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #eee; }
.btn-like { padding: 0.4rem 1rem; border: 1px solid #e74c3c; color: #e74c3c; background: #fff; border-radius: 4px; cursor: pointer; }
.btn-edit { padding: 0.4rem 1rem; border: 1px solid #333; background: #fff; border-radius: 4px; cursor: pointer; }
.btn-delete { padding: 0.4rem 1rem; border: none; background: #e74c3c; color: #fff; border-radius: 4px; cursor: pointer; }
.error { color: red; }
</style>
