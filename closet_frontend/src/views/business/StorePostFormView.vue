<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getDashboard, createStorePost, getStorePost, updateStorePost } from '@/api/business'

const router = useRouter()
const route = useRoute()

const isEdit = computed(() => !!route.params.pk)

const form = ref({ title: '', content: '', store_location: '' })
const existingImages = ref([])
const existingVideos = ref([])
const imageIdsToDelete = ref(new Set())
const videoIdsToDelete = ref(new Set())
const imageFiles = ref([])   // { file, previewUrl }
const videoFiles = ref([])   // { file }
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')

const imageInputRef = ref(null)
const videoInputRef = ref(null)

onMounted(async () => {
  isLoading.value = true
  try {
    const dashboard = await getDashboard()
    const profileAddress = dashboard.store_summary?.store_address || ''

    if (isEdit.value) {
      const post = await getStorePost(route.params.pk)
      form.value.title = post.title
      form.value.content = post.content
      form.value.store_location = post.store_location || profileAddress
      existingImages.value = post.images || []
      existingVideos.value = post.videos || []
    } else {
      form.value.store_location = profileAddress
    }
  } catch {
    errorMessage.value = '데이터를 불러오지 못했습니다.'
  } finally {
    isLoading.value = false
  }
})

function toggleDeleteImage(id) {
  const s = new Set(imageIdsToDelete.value)
  s.has(id) ? s.delete(id) : s.add(id)
  imageIdsToDelete.value = s
}

function toggleDeleteVideo(id) {
  const s = new Set(videoIdsToDelete.value)
  s.has(id) ? s.delete(id) : s.add(id)
  videoIdsToDelete.value = s
}

function onImageChange(e) {
  const newFiles = Array.from(e.target.files)
  newFiles.forEach((file) => {
    const isDuplicate = imageFiles.value.some(
      (item) => item.file.name === file.name && item.file.size === file.size
    )
    if (!isDuplicate) {
      imageFiles.value.push({ file, previewUrl: URL.createObjectURL(file) })
    }
  })
  e.target.value = ''
}

function removeNewImage(index) {
  URL.revokeObjectURL(imageFiles.value[index].previewUrl)
  imageFiles.value.splice(index, 1)
}

function onVideoChange(e) {
  const newFiles = Array.from(e.target.files)
  newFiles.forEach((file) => {
    const isDuplicate = videoFiles.value.some(
      (item) => item.file.name === file.name && item.file.size === file.size
    )
    if (!isDuplicate) {
      videoFiles.value.push({ file })
    }
  })
  e.target.value = ''
}

function removeNewVideo(index) {
  videoFiles.value.splice(index, 1)
}

async function handleSubmit() {
  if (!form.value.title.trim()) {
    alert('제목을 입력해주세요.')
    return
  }

  const formData = new FormData()
  formData.append('title', form.value.title)
  formData.append('content', form.value.content)
  formData.append('store_location', form.value.store_location)
  imageIdsToDelete.value.forEach((id) => formData.append('delete_image_ids', id))
  videoIdsToDelete.value.forEach((id) => formData.append('delete_video_ids', id))
  imageFiles.value.forEach(({ file }) => formData.append('images', file))
  videoFiles.value.forEach(({ file }) => formData.append('videos', file))

  isSaving.value = true
  errorMessage.value = ''
  try {
    if (isEdit.value) {
      await updateStorePost(route.params.pk, formData)
    } else {
      await createStorePost(formData)
    }
    router.push({ name: 'business-dashboard' })
  } catch (err) {
    errorMessage.value = err?.response?.data?.detail || '저장에 실패했습니다.'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <main class="store-form">
    <h1 class="store-form__title">{{ isEdit ? '가게 홍보 글 수정' : '가게 홍보 글 작성' }}</h1>

    <div v-if="isLoading" class="store-form__status">불러오는 중...</div>

    <form v-else @submit.prevent="handleSubmit" class="store-form__form">
      <div v-if="errorMessage" class="store-form__error">{{ errorMessage }}</div>

      <div class="store-form__field">
        <label class="store-form__label">제목 <span class="required">*</span></label>
        <input
          v-model="form.title"
          type="text"
          class="store-form__input"
          placeholder="게시글 제목을 입력하세요"
          required
        />
      </div>

      <div class="store-form__field">
        <label class="store-form__label">가게 위치</label>
        <input
          :value="form.store_location"
          type="text"
          class="store-form__input store-form__input--readonly"
          readonly
        />
        <p class="store-form__hint">사업자 등록 주소가 자동으로 입력됩니다 (수정 불가).</p>
      </div>

      <div class="store-form__field">
        <label class="store-form__label">내용</label>
        <textarea
          v-model="form.content"
          class="store-form__textarea"
          rows="8"
          placeholder="게시글 내용을 입력하세요"
        ></textarea>
      </div>

      <!-- 이미지 섹션 -->
      <div class="store-form__field">
        <label class="store-form__label">이미지</label>

        <!-- 기존 이미지 (수정 모드) -->
        <div v-if="existingImages.length" class="media-section-label">등록된 이미지</div>
        <div v-if="existingImages.length" class="media-grid">
          <div
            v-for="img in existingImages"
            :key="img.id"
            class="media-item"
            :class="{ 'media-item--deleted': imageIdsToDelete.has(img.id) }"
          >
            <img :src="img.image_url" class="media-item__thumb" />
            <button type="button" class="media-item__btn" @click="toggleDeleteImage(img.id)">
              {{ imageIdsToDelete.has(img.id) ? '취소' : '삭제' }}
            </button>
          </div>
        </div>

        <!-- 새로 추가할 이미지 미리보기 -->
        <div v-if="imageFiles.length" class="media-section-label">추가할 이미지</div>
        <div v-if="imageFiles.length" class="media-grid">
          <div v-for="(item, i) in imageFiles" :key="i" class="media-item">
            <img :src="item.previewUrl" class="media-item__thumb" />
            <button type="button" class="media-item__btn media-item__btn--remove" @click="removeNewImage(i)">
              제거
            </button>
          </div>
        </div>

        <input
          ref="imageInputRef"
          type="file"
          accept="image/*"
          multiple
          style="display: none"
          @change="onImageChange"
        />
        <button type="button" class="add-file-btn" @click="imageInputRef.click()">
          + 이미지 추가
        </button>
      </div>

      <!-- 동영상 섹션 -->
      <div class="store-form__field">
        <label class="store-form__label">동영상</label>

        <!-- 기존 영상 (수정 모드) -->
        <div v-if="existingVideos.length" class="media-section-label">등록된 동영상</div>
        <div v-if="existingVideos.length" class="media-grid">
          <div
            v-for="vid in existingVideos"
            :key="vid.id"
            class="media-item"
            :class="{ 'media-item--deleted': videoIdsToDelete.has(vid.id) }"
          >
            <video :src="vid.video_url" class="media-item__thumb" preload="metadata" />
            <button type="button" class="media-item__btn" @click="toggleDeleteVideo(vid.id)">
              {{ videoIdsToDelete.has(vid.id) ? '취소' : '삭제' }}
            </button>
          </div>
        </div>

        <!-- 새로 추가할 영상 목록 -->
        <div v-if="videoFiles.length" class="media-section-label">추가할 동영상</div>
        <ul v-if="videoFiles.length" class="video-list">
          <li v-for="(item, i) in videoFiles" :key="i" class="video-list__item">
            <span class="video-list__name">{{ item.file.name }}</span>
            <button type="button" class="media-item__btn media-item__btn--remove video-list__remove" @click="removeNewVideo(i)">
              제거
            </button>
          </li>
        </ul>

        <input
          ref="videoInputRef"
          type="file"
          accept="video/*"
          multiple
          style="display: none"
          @change="onVideoChange"
        />
        <button type="button" class="add-file-btn" @click="videoInputRef.click()">
          + 동영상 추가
        </button>
      </div>

      <div class="store-form__actions">
        <button
          type="button"
          class="store-form__cancel-btn"
          @click="router.push({ name: 'business-dashboard' })"
        >
          취소
        </button>
        <button type="submit" class="store-form__submit-btn" :disabled="isSaving">
          {{ isSaving ? '저장 중...' : isEdit ? '수정 완료' : '작성 완료' }}
        </button>
      </div>
    </form>
  </main>
</template>

<style scoped>
.store-form {
  max-width: 700px;
  margin: 0 auto;
  padding: 24px 16px;
}
.store-form__title {
  font-size: 1.4rem;
  font-weight: 700;
  margin-bottom: 24px;
}
.store-form__status {
  text-align: center;
  color: #888;
  padding: 24px;
}
.store-form__form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.store-form__error {
  padding: 12px;
  background: #fde8e8;
  border-radius: 6px;
  color: #c0392b;
  font-size: 0.9rem;
}
.store-form__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.store-form__label {
  font-weight: 500;
  font-size: 0.9rem;
  color: #444;
}
.required {
  color: #e74c3c;
}
.store-form__input,
.store-form__textarea {
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.95rem;
  outline: none;
}
.store-form__input:focus,
.store-form__textarea:focus {
  border-color: #666;
}
.store-form__textarea {
  resize: vertical;
}
.store-form__hint {
  font-size: 0.8rem;
  color: #999;
}
.store-form__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 8px;
}
.store-form__cancel-btn {
  padding: 10px 20px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 0.95rem;
  color: #555;
}
.store-form__submit-btn {
  padding: 10px 24px;
  background: #333;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
}
.store-form__submit-btn:disabled {
  background: #999;
  cursor: not-allowed;
}
.store-form__input--readonly {
  background: #f5f5f5;
  color: #888;
  cursor: not-allowed;
}

/* 미디어 그리드 */
.media-section-label {
  font-size: 0.8rem;
  color: #888;
  margin-top: 4px;
}
.media-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.media-item {
  position: relative;
  width: 120px;
}
.media-item__thumb {
  width: 120px;
  height: 90px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid #ddd;
  display: block;
}
.media-item--deleted .media-item__thumb {
  opacity: 0.35;
}
.media-item__btn {
  margin-top: 4px;
  width: 100%;
  padding: 4px 0;
  font-size: 0.78rem;
  border-radius: 4px;
  border: 1px solid #ddd;
  background: #fff;
  cursor: pointer;
  color: #c0392b;
}
.media-item--deleted .media-item__btn {
  color: #555;
  background: #f5f5f5;
}
.media-item__btn--remove {
  color: #888;
}

/* 동영상 파일 목록 */
.video-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.video-list__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #f9f9f9;
  border: 1px solid #eee;
  border-radius: 6px;
}
.video-list__name {
  flex: 1;
  font-size: 0.88rem;
  color: #555;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.video-list__remove {
  width: auto;
  padding: 3px 10px;
  margin-top: 0;
}

/* 파일 추가 버튼 */
.add-file-btn {
  align-self: flex-start;
  padding: 7px 16px;
  font-size: 0.88rem;
  border: 1px dashed #aaa;
  border-radius: 6px;
  background: #fafafa;
  color: #555;
  cursor: pointer;
}
.add-file-btn:hover {
  background: #f0f0f0;
}
</style>
