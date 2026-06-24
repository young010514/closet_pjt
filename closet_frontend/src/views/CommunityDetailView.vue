<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCommunityStore } from '@/stores/community'
import { checkApplication, submitApplication, fetchComments, createComment, updateComment, deleteComment } from '@/api/community'

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
const authorProfile = computed(() => post.value?.author_profile ?? null)
const authorDisplayName = computed(
  () => authorProfile.value?.nickname ?? post.value?.author_name ?? '익명',
)
const isAuthorSelf = computed(
  () => Boolean(authorProfile.value && authStore.user?.id === authorProfile.value.id),
)
const isRecruit = computed(() => post.value?.board === 'experience' && post.value?.category === 'recruit')
const isReview = computed(() => post.value?.board === 'experience' && post.value?.category === 'review')

// 체험단 신청
const showApplyForm = ref(false)
const alreadyApplied = ref(false)
const applySuccess = ref(false)
const applyError = ref('')
const applyFormRef = ref(null)
const applyForm = reactive({ name: '', phone: '', sns_account: '', motivation: '' })

onMounted(async () => {
  await store.fetchPost(pk)
  await loadComments()
  if (isRecruit.value && authStore.isAuthenticated) {
    try {
      const res = await checkApplication(pk)
      alreadyApplied.value = res.data.applied
    } catch {}
  }
})

function goToList() {
  const board = post.value?.board ?? 'fashion'
  router.push({ name: 'community', params: { board } })
}

async function handleLike() {
  try { await store.likePost(pk) }
  catch { alert('좋아요 처리에 실패했습니다.') }
}

function openApplyForm() {
  if (!authStore.isAuthenticated) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  showApplyForm.value = true
  setTimeout(() => applyFormRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
}

async function submitApply() {
  applyError.value = ''
  if (!applyForm.name.trim()) { applyError.value = '이름을 입력해주세요.'; return }
  if (!applyForm.phone.trim()) { applyError.value = '연락처를 입력해주세요.'; return }
  if (!applyForm.motivation.trim()) { applyError.value = '신청 동기를 입력해주세요.'; return }
  try {
    await submitApplication(pk, { ...applyForm })
    applySuccess.value = true
    alreadyApplied.value = true
    showApplyForm.value = false
  } catch (e) {
    applyError.value = e.response?.data?.detail || '신청에 실패했습니다.'
  }
}

// 댓글
const comments = ref([])
const newCommentContent = ref('')
const commentSubmitting = ref(false)
const editingCommentId = ref(null)
const editingContent = ref('')

async function loadComments() {
  try {
    const res = await fetchComments(pk)
    comments.value = res.data
  } catch {}
}

async function submitComment() {
  if (!newCommentContent.value.trim()) return
  commentSubmitting.value = true
  try {
    const res = await createComment(pk, { content: newCommentContent.value.trim() })
    comments.value.push(res.data)
    newCommentContent.value = ''
  } catch (e) {
    alert(e.response?.data?.detail || '댓글 작성에 실패했습니다.')
  } finally {
    commentSubmitting.value = false
  }
}

function startEditComment(comment) {
  editingCommentId.value = comment.id
  editingContent.value = comment.content
}

function cancelEditComment() {
  editingCommentId.value = null
  editingContent.value = ''
}

async function saveEditComment(comment) {
  if (!editingContent.value.trim()) return
  try {
    const res = await updateComment(pk, comment.id, { content: editingContent.value.trim() })
    const idx = comments.value.findIndex(c => c.id === comment.id)
    if (idx !== -1) comments.value[idx] = res.data
    cancelEditComment()
  } catch (e) {
    alert(e.response?.data?.detail || '댓글 수정에 실패했습니다.')
  }
}

async function removeComment(commentId) {
  if (!confirm('댓글을 삭제하시겠습니까?')) return
  try {
    await deleteComment(pk, commentId)
    comments.value = comments.value.filter(c => c.id !== commentId)
  } catch (e) {
    alert(e.response?.data?.detail || '댓글 삭제에 실패했습니다.')
  }
}

async function handleDelete() {
  if (!confirm('게시글을 삭제하시겠습니까?')) return
  const board = post.value?.board ?? 'fashion'
  try {
    await store.deletePost(pk)
    router.push({ name: 'community', params: { board } })
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
        <div class="author-meta">
          <RouterLink
            v-if="authorProfile"
            class="author-link"
            :to="{ name: 'user-profile', params: { userId: authorProfile.id } }"
          >
            <span class="author-name">{{ authorDisplayName }}</span>
            <span class="author-username">@{{ authorProfile.username }}</span>
          </RouterLink>
          <template v-else>
            <span class="author-name">{{ authorDisplayName }}</span>
          </template>
        </div>

      </div>

      <!-- 이미지 갤러리 -->
      <div v-if="post.images?.length" class="image-gallery">
        <img v-for="img in post.images" :key="img.id" :src="img.image_url" alt="이미지" />
      </div>

      <!-- 영상 갤러리 -->
      <div v-if="post.videos?.length" class="video-gallery">
        <video
          v-for="v in post.videos"
          :key="v.id"
          :src="v.video_url"
          controls
          class="post-video"
        />
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

      <!-- 댓글 섹션 -->
      <section class="comments-section">
        <h3 class="comments-title">댓글 <span class="comment-count">{{ comments.length }}</span></h3>

        <!-- 댓글 목록 -->
        <ul class="comment-list">
          <li v-for="comment in comments" :key="comment.id" class="comment-item">
            <div v-if="editingCommentId === comment.id" class="comment-edit-form">
              <textarea v-model="editingContent" rows="3" class="comment-textarea" />
              <div class="comment-edit-actions">
                <button class="btn-comment-cancel" @click="cancelEditComment">취소</button>
                <button class="btn-comment-save" @click="saveEditComment(comment)">저장</button>
              </div>
            </div>
            <div v-else class="comment-body">
              <div class="comment-header">
                <span class="comment-author">{{ comment.author_name }}</span>
                <span class="comment-date">{{ new Date(comment.created_at).toLocaleDateString() }}</span>
                <template v-if="comment.is_author">
                  <button class="btn-comment-edit" @click="startEditComment(comment)">수정</button>
                  <button class="btn-comment-delete" @click="removeComment(comment.id)">삭제</button>
                </template>
              </div>
              <p class="comment-content">{{ comment.content }}</p>
            </div>
          </li>
          <li v-if="comments.length === 0" class="comment-empty">첫 번째 댓글을 작성해보세요.</li>
        </ul>

        <!-- 댓글 작성 폼 -->
        <div v-if="authStore.isAuthenticated" class="comment-form">
          <textarea
            v-model="newCommentContent"
            rows="3"
            class="comment-textarea"
            placeholder="댓글을 입력하세요."
            @keydown.ctrl.enter="submitComment"
          />
          <div class="comment-form-actions">
            <span class="comment-hint">Ctrl+Enter로 등록</span>
            <button class="btn-comment-submit" :disabled="commentSubmitting || !newCommentContent.trim()" @click="submitComment">
              {{ commentSubmitting ? '등록 중...' : '댓글 등록' }}
            </button>
          </div>
        </div>
        <p v-else class="comment-login-notice">
          댓글을 작성하려면 <button class="btn-login-link" @click="router.push('/login')">로그인</button>이 필요합니다.
        </p>
      </section>

      <!-- 체험단 신청 버튼 (모집중인 경우만) -->
      <template v-if="isRecruit && post.experience_status === 'recruiting'">
        <div class="apply-cta">
          <p v-if="applySuccess" class="apply-done">신청이 완료되었습니다! 연락을 기다려 주세요.</p>
          <p v-else-if="alreadyApplied" class="apply-done">이미 신청하신 체험단입니다.</p>
          <button v-else class="btn-apply" @click="openApplyForm">체험단 신청하기</button>
        </div>

        <!-- 신청 폼 (스크롤 타겟) -->
        <section v-if="showApplyForm" ref="applyFormRef" class="apply-form-section">
          <h3>체험단 신청</h3>
          <p class="apply-desc">아래 정보를 입력하시면 가게 측에서 검토 후 연락드립니다.</p>
          <p v-if="applyError" class="apply-error">{{ applyError }}</p>

          <form class="apply-form" @submit.prevent="submitApply">
            <div class="apply-field">
              <label>이름 <span class="req">*</span></label>
              <input v-model="applyForm.name" type="text" placeholder="실명을 입력해주세요" />
            </div>
            <div class="apply-field">
              <label>연락처 <span class="req">*</span></label>
              <input v-model="applyForm.phone" type="tel" placeholder="010-0000-0000" />
            </div>
            <div class="apply-field">
              <label>SNS 채널 <span class="optional">(선택)</span></label>
              <input v-model="applyForm.sns_account" type="text" placeholder="인스타그램 아이디 또는 블로그 URL" />
            </div>
            <div class="apply-field">
              <label>신청 동기 <span class="req">*</span></label>
              <textarea
                v-model="applyForm.motivation"
                rows="5"
                placeholder="이 체험단에 참여하고 싶은 이유와 활동 계획을 자유롭게 작성해 주세요."
              />
            </div>
            <div class="apply-actions">
              <button type="button" class="btn-cancel" @click="showApplyForm = false">취소</button>
              <button type="submit" class="btn-submit">신청 완료</button>
            </div>
          </form>
        </section>
      </template>
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

.meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  font-size: 0.8rem;
  color: #888;
  margin-bottom: 1rem;
}
.author-meta {
  display: grid;
  gap: 0.15rem;
  min-width: 0;
}
.author-link {
  display: grid;
  gap: 0.15rem;
  color: inherit;
  text-decoration: none;
}
.author-link:hover .author-name {
  text-decoration: underline;
}
.author-name {
  color: #222;
  font-size: 0.9rem;
  font-weight: 700;
}
.author-username {
  color: #8a8a8a;
  font-size: 0.78rem;
}

.image-gallery {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.5rem; margin: 1rem 0;
}
.image-gallery img {
  width: 100%; aspect-ratio: 4/3; object-fit: cover;
  border-radius: 6px; border: 1px solid #eee;
}

.video-gallery {
  display: flex; flex-direction: column; gap: 0.75rem; margin: 1rem 0;
}
.post-video {
  width: 100%; max-width: 700px; border-radius: 6px; border: 1px solid #eee;
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

/* 체험단 신청 */
.apply-cta {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 2px solid #eee;
  text-align: center;
}
.btn-apply {
  padding: 0.75rem 2.5rem;
  background: #3c5fbe;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-apply:hover { background: #2d4a9a; }
.apply-done {
  font-size: 0.95rem;
  color: #1e7e34;
  font-weight: 500;
  padding: 0.75rem 1rem;
  background: #e6f4ea;
  border-radius: 6px;
  display: inline-block;
}

.apply-form-section {
  margin-top: 2rem;
  padding: 1.5rem;
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
}
.apply-form-section h3 {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 0.3rem;
}
.apply-desc { font-size: 0.85rem; color: #888; margin-bottom: 1.2rem; }
.apply-error { color: #c0392b; font-size: 0.88rem; margin-bottom: 0.75rem; }

.apply-form { display: flex; flex-direction: column; gap: 1rem; }
.apply-field { display: flex; flex-direction: column; gap: 0.3rem; }
.apply-field label { font-size: 0.88rem; font-weight: 500; }
.req { color: #e74c3c; }
.optional { color: #aaa; font-weight: normal; font-size: 0.8rem; }
.apply-field input,
.apply-field textarea {
  padding: 0.55rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 5px;
  font-size: 0.93rem;
  background: #fff;
}
.apply-field textarea { resize: vertical; }

.apply-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 0.5rem; }
.btn-cancel {
  padding: 0.5rem 1.2rem;
  border: 1px solid #ccc;
  background: #fff;
  border-radius: 5px;
  cursor: pointer;
}
.btn-submit {
  padding: 0.5rem 1.5rem;
  background: #3c5fbe;
  color: #fff;
  border: none;
  border-radius: 5px;
  font-weight: 600;
  cursor: pointer;
}
.btn-submit:hover { background: #2d4a9a; }

/* 댓글 */
.comments-section {
  margin-top: 2.5rem;
  padding-top: 1.5rem;
  border-top: 2px solid #eee;
}
.comments-title {
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 1rem;
}
.comment-count {
  font-size: 0.9rem;
  color: #3c5fbe;
  margin-left: 0.3rem;
}
.comment-list {
  list-style: none;
  padding: 0;
  margin: 0 0 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.comment-item {
  padding: 0.75rem 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #eee;
}
.comment-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
  font-size: 0.82rem;
}
.comment-author { font-weight: 600; color: #333; }
.comment-date { color: #aaa; flex: 1; }
.btn-comment-edit,
.btn-comment-delete {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.78rem;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
}
.btn-comment-edit { color: #555; }
.btn-comment-edit:hover { background: #e9ecef; }
.btn-comment-delete { color: #c0392b; }
.btn-comment-delete:hover { background: #fdecea; }
.comment-content { font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap; margin: 0; }
.comment-empty { color: #aaa; font-size: 0.88rem; text-align: center; padding: 1.5rem 0; }

.comment-edit-form { display: flex; flex-direction: column; gap: 0.5rem; }
.comment-edit-actions { display: flex; gap: 0.4rem; justify-content: flex-end; }
.btn-comment-cancel {
  padding: 0.3rem 0.8rem;
  border: 1px solid #ccc;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.82rem;
}
.btn-comment-save {
  padding: 0.3rem 0.8rem;
  background: #3c5fbe;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 600;
}

.comment-form { display: flex; flex-direction: column; gap: 0.5rem; }
.comment-textarea {
  width: 100%;
  padding: 0.6rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 0.9rem;
  resize: vertical;
  box-sizing: border-box;
}
.comment-textarea:focus { outline: none; border-color: #3c5fbe; }
.comment-form-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
}
.comment-hint { font-size: 0.78rem; color: #aaa; }
.btn-comment-submit {
  padding: 0.45rem 1.2rem;
  background: #3c5fbe;
  color: #fff;
  border: none;
  border-radius: 5px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
}
.btn-comment-submit:disabled { background: #aaa; cursor: not-allowed; }
.btn-comment-submit:not(:disabled):hover { background: #2d4a9a; }

.comment-login-notice { font-size: 0.88rem; color: #888; text-align: center; padding: 0.75rem; }
.btn-login-link {
  background: none;
  border: none;
  color: #3c5fbe;
  cursor: pointer;
  font-size: inherit;
  text-decoration: underline;
  padding: 0;
}
</style>
