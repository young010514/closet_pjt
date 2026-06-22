<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCommunityStore } from '@/stores/community'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({ isEdit: { type: Boolean, default: false } })

const route = useRoute()
const router = useRouter()
const store = useCommunityStore()
const authStore = useAuthStore()

const pk = props.isEdit ? Number(route.params.pk) : null
const error = ref('')
const imageFiles = ref([])
const imagePreviewUrls = ref([])
const existingImages = ref([])

const NOTICE_TEMPLATE = `■ 체험단 인원:
■ 신청 방법:
■ 제공 혜택:
■ 후기 작성 기간:
■ 주의 사항:
  - 체험 후 SNS 또는 블로그에 솔직한 후기를 작성해 주세요.
  - 제공된 제품은 반납하지 않아도 됩니다.`

const form = reactive({
  board: 'fashion',
  title: '',
  content: '',
  gender: '',
  category: 'top',
  hashtags: '',
  // 체험단 공통
  store_name: '',
  // 체험단 모집 전용
  store_location: '',
  product_description: '',
  notice: NOTICE_TEMPLATE,
  recruit_start: '',
  recruit_end: '',
  experience_end: '',
  // 체험단 후기 전용
  experience_participation_start: '',
  experience_participation_end: '',
})

const BOARD_OPTIONS = [
  { value: 'fashion', label: '패션 정보 공유' },
  { value: 'daily', label: '일상 & 소통' },
  { value: 'local_shop', label: '우리 동네 가게' },
  { value: 'experience', label: '체험단' },
]

const GENDER_OPTIONS = [
  { value: '', label: '선택 안 함' },
  { value: 'male', label: '남성' },
  { value: 'female', label: '여성' },
  { value: 'kids', label: '키즈' },
]

const FASHION_CATEGORIES = [
  { value: 'top', label: '상의' },
  { value: 'bottom', label: '하의' },
  { value: 'outer', label: '아우터' },
  { value: 'shoes', label: '슈즈' },
  { value: 'accessories', label: '잡화·악세사리' },
]

const DAILY_CATEGORIES = [
  { value: 'lifestyle', label: '라이프스타일' },
  { value: 'counseling', label: '고민·상담' },
]

const EXPERIENCE_CATEGORIES = [
  { value: 'recruit', label: '체험단 모집' },
  { value: 'review', label: '체험단 후기' },
]

const showGender = computed(() => form.board === 'fashion')
const showCategory = computed(() => ['fashion', 'daily', 'experience'].includes(form.board))
const isExperienceRecruit = computed(() => form.board === 'experience' && form.category === 'recruit')
const isExperienceReview = computed(() => form.board === 'experience' && form.category === 'review')
const isExperience = computed(() => form.board === 'experience')

const categoryOptions = computed(() => {
  if (form.board === 'fashion') return FASHION_CATEGORIES
  if (form.board === 'daily') return DAILY_CATEGORIES
  if (form.board === 'experience') return EXPERIENCE_CATEGORIES
  return []
})

const permissionWarning = computed(() => {
  if (form.board !== 'experience') return ''
  if (form.category === 'recruit' && !authStore.isBusinessUser)
    return '체험단 모집 글은 사업자 회원만 작성할 수 있습니다.'
  if (form.category === 'review' && !authStore.isNormalUser)
    return '체험단 후기 글은 일반 회원만 작성할 수 있습니다.'
  return ''
})

const canSubmit = computed(() => !permissionWarning.value)

const minImages = computed(() => isExperienceRecruit.value ? 2 : (isExperienceReview.value ? 1 : 0))

watch(() => form.board, (newBoard) => {
  form.gender = ''
  form.store_name = ''
  form.store_location = ''
  form.product_description = ''
  form.notice = NOTICE_TEMPLATE
  form.recruit_start = ''
  form.recruit_end = ''
  form.experience_end = ''
  form.experience_participation_start = ''
  form.experience_participation_end = ''
  imageFiles.value = []
  imagePreviewUrls.value = []

  if (newBoard === 'fashion') form.category = 'top'
  else if (newBoard === 'daily') form.category = 'lifestyle'
  else if (newBoard === 'experience') form.category = 'recruit'
  else form.category = ''
})

watch(() => form.category, () => {
  form.recruit_start = ''
  form.recruit_end = ''
  form.experience_end = ''
  form.experience_participation_start = ''
  form.experience_participation_end = ''
  imageFiles.value = []
  imagePreviewUrls.value = []
})

function onImagesChange(e) {
  const files = Array.from(e.target.files)
  imageFiles.value = files
  imagePreviewUrls.value = files.map((f) => URL.createObjectURL(f))
}

function removeImage(idx) {
  imageFiles.value = imageFiles.value.filter((_, i) => i !== idx)
  imagePreviewUrls.value = imagePreviewUrls.value.filter((_, i) => i !== idx)
}

onMounted(async () => {
  if (props.isEdit && pk) {
    await store.fetchPost(pk)
    const p = store.currentPost
    if (p) {
      form.board = p.board
      form.title = p.title
      form.content = p.content
      form.gender = p.gender ?? ''
      form.category = p.category
      form.hashtags = p.hashtags.join(' ')
      form.store_name = p.store_name ?? ''
      form.store_location = p.store_location ?? ''
      form.product_description = p.product_description ?? ''
      form.notice = p.notice || NOTICE_TEMPLATE
      form.recruit_start = p.recruit_start ?? ''
      form.recruit_end = p.recruit_end ?? ''
      form.experience_end = p.experience_end ?? ''
      form.experience_participation_start = p.experience_participation_start ?? ''
      form.experience_participation_end = p.experience_participation_end ?? ''
      existingImages.value = p.images ?? []
    }
  }
})

function buildPayload() {
  const payload = {
    board: form.board,
    title: form.title,
    gender: showGender.value ? (form.gender || null) : null,
    category: showCategory.value ? form.category : '',
    hashtags: form.hashtags.split(/\s+/).map((t) => t.trim()).filter(Boolean),
  }

  if (isExperienceRecruit.value) {
    payload.store_name = form.store_name
    payload.store_location = form.store_location
    payload.product_description = form.product_description
    payload.notice = form.notice
    payload.recruit_start = form.recruit_start || null
    payload.recruit_end = form.recruit_end || null
    payload.experience_end = form.experience_end || null
    payload.content = ''
  } else if (isExperienceReview.value) {
    payload.store_name = form.store_name
    payload.content = form.content
    payload.experience_participation_start = form.experience_participation_start || null
    payload.experience_participation_end = form.experience_participation_end || null
  } else {
    payload.content = form.content
  }

  if (imageFiles.value.length > 0) {
    payload.images = imageFiles.value
  }

  return payload
}

async function submit() {
  error.value = ''

  if (permissionWarning.value) {
    error.value = permissionWarning.value
    return
  }
  if (!form.title.trim()) {
    error.value = '제목을 입력해주세요.'
    return
  }
  if (isExperienceRecruit.value) {
    if (!form.store_name.trim()) { error.value = '가게 상호명을 입력해주세요.'; return }
    if (!form.store_location.trim()) { error.value = '가게 위치를 입력해주세요.'; return }
    if (!form.product_description.trim()) { error.value = '상품 설명을 입력해주세요.'; return }
    if (imageFiles.value.length < 2 && existingImages.value.length < 2) {
      error.value = '상품 이미지를 2장 이상 등록해주세요.'; return
    }
  } else if (isExperienceReview.value) {
    if (!form.store_name.trim()) { error.value = '가게 상호명을 입력해주세요.'; return }
    if (!form.content.trim()) { error.value = '체험단 후기를 작성해주세요.'; return }
    if (imageFiles.value.length < 1 && existingImages.value.length < 1) {
      error.value = '상품 이미지를 1장 이상 등록해주세요.'; return
    }
  } else {
    if (!form.content.trim()) { error.value = '내용을 입력해주세요.'; return }
  }

  try {
    if (props.isEdit) {
      await store.updatePost(pk, buildPayload())
      router.push(`/community/${pk}`)
    } else {
      const post = await store.createPost(buildPayload())
      router.push(`/community/${post.id}`)
    }
  } catch (e) {
    error.value = e.response?.data ? JSON.stringify(e.response.data) : '저장에 실패했습니다.'
  }
}
</script>

<template>
  <div class="community-form">
    <h2>{{ isEdit ? '게시글 수정' : '게시글 작성' }}</h2>
    <p v-if="error" class="error">{{ error }}</p>

    <form @submit.prevent="submit">
      <!-- 게시판 선택 -->
      <div class="field">
        <label>게시판</label>
        <select v-model="form.board">
          <option v-for="o in BOARD_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
      </div>

      <!-- 카테고리 (패션/일상/체험단) -->
      <template v-if="showCategory">
        <div class="field">
          <label>카테고리</label>
          <select v-model="form.category">
            <option v-for="o in categoryOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
      </template>

      <!-- 체험단 권한 경고 -->
      <div v-if="permissionWarning" class="permission-warning">{{ permissionWarning }}</div>

      <!-- ===== 체험단 모집 전용 필드 ===== -->
      <template v-if="isExperienceRecruit">
        <div class="field">
          <label>가게 상호명 <span class="required">*</span></label>
          <input v-model="form.store_name" type="text" placeholder="가게 상호명을 입력하세요" />
        </div>
        <div class="field">
          <label>가게 위치 <span class="required">*</span></label>
          <input v-model="form.store_location" type="text" placeholder="예: 서울시 강남구 역삼동 123-4" />
        </div>
        <div class="field">
          <label>제목 <span class="required">*</span></label>
          <input v-model="form.title" type="text" placeholder="제목을 입력하세요" />
        </div>
        <div class="field">
          <label>상품 설명 <span class="required">*</span></label>
          <textarea v-model="form.product_description" rows="4" placeholder="체험단에서 제공하는 상품을 설명해주세요"></textarea>
        </div>
        <div class="field">
          <label>상품 이미지 <span class="required">*</span> <small>(최소 2장)</small></label>
          <input type="file" accept="image/*" multiple @change="onImagesChange" />
          <div v-if="imagePreviewUrls.length" class="image-preview-grid">
            <div v-for="(url, idx) in imagePreviewUrls" :key="idx" class="preview-item">
              <img :src="url" alt="미리보기" />
              <button type="button" class="remove-img" @click="removeImage(idx)">✕</button>
            </div>
          </div>
          <div v-else-if="existingImages.length" class="image-preview-grid">
            <div v-for="img in existingImages" :key="img.id" class="preview-item">
              <img :src="img.image_url" alt="기존 이미지" />
            </div>
          </div>
        </div>
        <div class="field">
          <label>모집 시작일 <span class="required">*</span></label>
          <input v-model="form.recruit_start" type="date" />
        </div>
        <div class="field">
          <label>모집 마감일 <span class="required">*</span></label>
          <input v-model="form.recruit_end" type="date" />
        </div>
        <div class="field">
          <label>체험단 종료일 <span class="required">*</span></label>
          <input v-model="form.experience_end" type="date" />
        </div>
        <div class="field">
          <label>공지 사항</label>
          <textarea v-model="form.notice" rows="8"></textarea>
        </div>
      </template>

      <!-- ===== 체험단 후기 전용 필드 ===== -->
      <template v-else-if="isExperienceReview">
        <div class="field">
          <label>가게 상호명 <span class="required">*</span></label>
          <input v-model="form.store_name" type="text" placeholder="방문한 가게 상호명을 입력하세요" />
        </div>
        <div class="field">
          <label>제목 <span class="required">*</span></label>
          <input v-model="form.title" type="text" placeholder="제목을 입력하세요" />
        </div>
        <div class="field">
          <label>체험단 참여 기간</label>
          <div class="date-range">
            <input v-model="form.experience_participation_start" type="date" />
            <span>~</span>
            <input v-model="form.experience_participation_end" type="date" />
          </div>
        </div>
        <div class="field">
          <label>상품 이미지 <span class="required">*</span></label>
          <input type="file" accept="image/*" multiple @change="onImagesChange" />
          <div v-if="imagePreviewUrls.length" class="image-preview-grid">
            <div v-for="(url, idx) in imagePreviewUrls" :key="idx" class="preview-item">
              <img :src="url" alt="미리보기" />
              <button type="button" class="remove-img" @click="removeImage(idx)">✕</button>
            </div>
          </div>
          <div v-else-if="existingImages.length" class="image-preview-grid">
            <div v-for="img in existingImages" :key="img.id" class="preview-item">
              <img :src="img.image_url" alt="기존 이미지" />
            </div>
          </div>
        </div>
        <div class="field">
          <label>체험단 후기 <span class="required">*</span></label>
          <textarea v-model="form.content" rows="10" placeholder="솔직한 체험 후기를 작성해주세요"></textarea>
        </div>
      </template>

      <!-- ===== 일반 게시판 필드 ===== -->
      <template v-else>
        <template v-if="showGender">
          <div class="field">
            <label>성별</label>
            <select v-model="form.gender">
              <option v-for="o in GENDER_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
            </select>
          </div>
        </template>
        <div class="field">
          <label>제목</label>
          <input v-model="form.title" type="text" placeholder="제목을 입력하세요" required />
        </div>
        <div class="field">
          <label>내용</label>
          <textarea v-model="form.content" rows="10" placeholder="내용을 입력하세요" required></textarea>
        </div>
        <div class="field">
          <label>해시태그 <small>(공백으로 구분, 예: #데일리 #코디)</small></label>
          <input v-model="form.hashtags" type="text" placeholder="#해시태그 #입력" />
        </div>
      </template>

      <div class="form-actions">
        <button type="button" @click="router.back()">취소</button>
        <button type="submit" :disabled="!canSubmit">{{ isEdit ? '수정 완료' : '등록' }}</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.community-form { max-width: 700px; margin: 0 auto; padding: 1rem; }
h2 { margin-bottom: 1.5rem; }
.field { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 1rem; }
label { font-size: 0.9rem; font-weight: 500; }
.required { color: #e74c3c; }
small { font-weight: normal; color: #888; }
input[type="text"], input[type="date"], select, textarea {
  padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; font-size: 0.95rem;
}
textarea { resize: vertical; }
.date-range { display: flex; align-items: center; gap: 0.5rem; }
.date-range input { flex: 1; }

/* 이미지 미리보기 */
.image-preview-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
.preview-item { position: relative; width: 100px; height: 100px; }
.preview-item img { width: 100%; height: 100%; object-fit: cover; border-radius: 4px; border: 1px solid #ddd; }
.remove-img {
  position: absolute; top: 2px; right: 2px;
  background: rgba(0,0,0,0.55); color: #fff; border: none;
  border-radius: 50%; width: 20px; height: 20px; font-size: 10px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
}

.permission-warning {
  background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;
  padding: 0.6rem 1rem; color: #856404; font-size: 0.9rem; margin-bottom: 1rem;
}
.form-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1rem; }
.form-actions button { padding: 0.5rem 1.5rem; border-radius: 4px; cursor: pointer; }
.form-actions button[type="submit"] { background: #333; color: #fff; border: none; }
.form-actions button[type="submit"]:disabled { background: #999; cursor: not-allowed; }
.form-actions button[type="button"] { background: #fff; border: 1px solid #ccc; }
.error { color: red; margin-bottom: 1rem; }
</style>
