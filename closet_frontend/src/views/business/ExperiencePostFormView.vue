<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createExperiencePost, getExperiencePost, updateExperiencePost } from '@/api/business'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.pk)
const errorMessage = ref('')
const isSubmitting = ref(false)

const form = ref({
  title: '',
  content: '',
  store_name: '',
  product_description: '',
  notice: '',
  recruit_start: '',
  recruit_end: '',
  experience_end: '',
})

onMounted(async () => {
  if (isEdit.value) {
    try {
      const post = await getExperiencePost(route.params.pk)
      form.value.title = post.title
      form.value.content = post.content
      form.value.store_name = post.store_name
      form.value.product_description = post.product_description
      form.value.notice = post.notice
      form.value.recruit_start = post.recruit_start || ''
      form.value.recruit_end = post.recruit_end || ''
      form.value.experience_end = post.experience_end || ''
    } catch {
      errorMessage.value = '공고를 불러오지 못했습니다.'
    }
  }
})

async function handleSubmit() {
  if (isSubmitting.value) return
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    const fd = new FormData()
    fd.append('title', form.value.title)
    fd.append('content', form.value.content)
    fd.append('store_name', form.value.store_name)
    fd.append('product_description', form.value.product_description)
    fd.append('notice', form.value.notice)
    fd.append('recruit_start', form.value.recruit_start)
    fd.append('recruit_end', form.value.recruit_end)
    fd.append('experience_end', form.value.experience_end)

    if (isEdit.value) {
      await updateExperiencePost(route.params.pk, fd)
    } else {
      await createExperiencePost(fd)
    }
    router.push({ name: 'business-dashboard' })
  } catch (err) {
    const detail = err?.response?.data
    if (typeof detail === 'object') {
      errorMessage.value = Object.values(detail).flat().join(' ')
    } else {
      errorMessage.value = '저장에 실패했습니다.'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="exp-form">
    <h1 class="exp-form__title">{{ isEdit ? '체험단 공고 수정' : '체험단 공고 등록' }}</h1>
    <div v-if="errorMessage" class="exp-form__error">{{ errorMessage }}</div>

    <form class="exp-form__body" @submit.prevent="handleSubmit">
      <label class="exp-form__label">제목 *</label>
      <input v-model="form.title" type="text" class="exp-form__input" required />

      <label class="exp-form__label">내용</label>
      <textarea v-model="form.content" class="exp-form__textarea" rows="4" />

      <label class="exp-form__label">가게명</label>
      <input v-model="form.store_name" type="text" class="exp-form__input" />

      <label class="exp-form__label">제품 설명</label>
      <textarea v-model="form.product_description" class="exp-form__textarea" rows="3" />

      <label class="exp-form__label">유의사항</label>
      <textarea v-model="form.notice" class="exp-form__textarea" rows="3" />

      <div class="exp-form__date-row">
        <div>
          <label class="exp-form__label">모집 시작일 *</label>
          <input v-model="form.recruit_start" type="date" class="exp-form__input" required />
        </div>
        <div>
          <label class="exp-form__label">모집 마감일 *</label>
          <input v-model="form.recruit_end" type="date" class="exp-form__input" required />
        </div>
        <div>
          <label class="exp-form__label">체험 종료일 *</label>
          <input v-model="form.experience_end" type="date" class="exp-form__input" required />
        </div>
      </div>

      <div class="exp-form__footer">
        <router-link :to="{ name: 'business-dashboard' }" class="exp-form__btn exp-form__btn--cancel">취소</router-link>
        <button type="submit" class="exp-form__btn exp-form__btn--submit" :disabled="isSubmitting">
          {{ isSubmitting ? '저장 중...' : isEdit ? '수정 완료' : '등록' }}
        </button>
      </div>
    </form>
  </main>
</template>

<style scoped>
.exp-form {
  max-width: 700px;
  margin: 0 auto;
  padding: 24px 16px;
}
.exp-form__title {
  font-size: 1.4rem;
  font-weight: 700;
  margin-bottom: 20px;
}
.exp-form__error {
  color: #c0392b;
  background: #fef2f2;
  border: 1px solid #fca5a5;
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 16px;
}
.exp-form__label {
  display: block;
  font-size: 0.9rem;
  font-weight: 600;
  color: #444;
  margin-bottom: 4px;
  margin-top: 14px;
}
.exp-form__input,
.exp-form__textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.95rem;
  box-sizing: border-box;
}
.exp-form__textarea { resize: vertical; }
.exp-form__date-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  margin-top: 14px;
}
.exp-form__footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}
.exp-form__btn {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 0.95rem;
  cursor: pointer;
  border: none;
  text-decoration: none;
  display: inline-block;
}
.exp-form__btn--cancel { background: #e5e7eb; color: #374151; }
.exp-form__btn--submit { background: #3b82f6; color: #fff; }
.exp-form__btn--submit:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
