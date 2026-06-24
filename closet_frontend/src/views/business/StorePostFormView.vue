<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getDashboard, createStorePost, getStorePost, updateStorePost } from '@/api/business'

const router = useRouter()
const route = useRoute()

const isEdit = computed(() => !!route.params.pk)

const form = ref({ title: '', content: '', store_location: '' })
const imageFiles = ref([])
const videoFiles = ref([])
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')

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
    } else {
      form.value.store_location = profileAddress
    }
  } catch {
    errorMessage.value = '데이터를 불러오지 못했습니다.'
  } finally {
    isLoading.value = false
  }
})

function onImageChange(e) {
  imageFiles.value = Array.from(e.target.files)
}

function onVideoChange(e) {
  videoFiles.value = Array.from(e.target.files)
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
  imageFiles.value.forEach((f) => formData.append('images', f))
  videoFiles.value.forEach((f) => formData.append('videos', f))

  isSaving.value = true
  errorMessage.value = ''
  try {
    if (isEdit.value) {
      await updateStorePost(route.params.pk, formData)
    } else {
      await createStorePost(formData)
    }
    router.push({ name: 'business-store' })
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

      <div class="store-form__field">
        <label class="store-form__label">이미지</label>
        <input type="file" accept="image/*" multiple @change="onImageChange" />
        <p v-if="imageFiles.length" class="store-form__hint">{{ imageFiles.length }}개 선택됨</p>
      </div>

      <div class="store-form__field">
        <label class="store-form__label">동영상</label>
        <input type="file" accept="video/*" multiple @change="onVideoChange" />
        <p v-if="videoFiles.length" class="store-form__hint">{{ videoFiles.length }}개 선택됨</p>
      </div>

      <div class="store-form__actions">
        <button
          type="button"
          class="store-form__cancel-btn"
          @click="router.push({ name: 'business-store' })"
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
</style>
