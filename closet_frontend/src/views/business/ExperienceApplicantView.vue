<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getExperienceApplicants, decideApplicant } from '@/api/business'

const route = useRoute()
const router = useRouter()
const applicants = ref([])
const isLoading = ref(false)
const errorMessage = ref('')

// 거절 모달 상태
const rejectModal = ref({ visible: false, applicationId: null, reason: '' })
const actionError = ref('')

onMounted(async () => {
  isLoading.value = true
  try {
    applicants.value = await getExperienceApplicants(route.params.pk)
  } catch (err) {
    if (err?.response?.status === 403) {
      errorMessage.value = '접근 권한이 없습니다.'
    } else {
      errorMessage.value = '신청자 목록을 불러오지 못했습니다.'
    }
  } finally {
    isLoading.value = false
  }
})

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function statusLabel(s) {
  if (s === 'approved') return '승인'
  if (s === 'rejected') return '거절'
  return '대기'
}

async function approve(applicationId) {
  actionError.value = ''
  try {
    const result = await decideApplicant(route.params.pk, applicationId, { status: 'approved' })
    const target = applicants.value.find((a) => a.id === applicationId)
    if (target) {
      target.status = result.status
      target.rejection_reason = result.rejection_reason
    }
  } catch (err) {
    actionError.value = err?.response?.data?.detail || '승인 처리 중 오류가 발생했습니다.'
  }
}

function openRejectModal(applicationId) {
  rejectModal.value = { visible: true, applicationId, reason: '' }
  actionError.value = ''
}

function closeRejectModal() {
  rejectModal.value = { visible: false, applicationId: null, reason: '' }
}

async function submitReject() {
  actionError.value = ''
  if (!rejectModal.value.reason.trim()) {
    actionError.value = '거절 사유를 입력해주세요.'
    return
  }
  try {
    const result = await decideApplicant(route.params.pk, rejectModal.value.applicationId, {
      status: 'rejected',
      rejection_reason: rejectModal.value.reason.trim(),
    })
    const target = applicants.value.find((a) => a.id === rejectModal.value.applicationId)
    if (target) {
      target.status = result.status
      target.rejection_reason = result.rejection_reason
    }
    closeRejectModal()
  } catch (err) {
    actionError.value = err?.response?.data?.detail || '거절 처리 중 오류가 발생했습니다.'
  }
}
</script>

<template>
  <main class="applicants">
    <button class="applicants__back" @click="router.push({ name: 'business-dashboard' })">← 목록으로</button>
    <h1 class="applicants__title">신청자 목록</h1>

    <div v-if="isLoading" class="applicants__status">불러오는 중...</div>
    <div v-else-if="errorMessage" class="applicants__status applicants__status--error">{{ errorMessage }}</div>
    <div v-else-if="applicants.length === 0" class="applicants__status">신청자가 없습니다.</div>

    <template v-else>
      <p v-if="actionError" class="applicants__action-error">{{ actionError }}</p>

      <table class="applicants__table">
        <thead>
          <tr>
            <th>#</th>
            <th>이름</th>
            <th>연락처</th>
            <th>SNS 계정</th>
            <th>지원 동기</th>
            <th>신청일</th>
            <th>상태</th>
            <th>관리</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(a, idx) in applicants" :key="a.id">
            <td>{{ idx + 1 }}</td>
            <td>{{ a.name }}</td>
            <td>{{ a.phone }}</td>
            <td>{{ a.sns_account || '-' }}</td>
            <td class="applicants__motivation">{{ a.motivation }}</td>
            <td>{{ formatDate(a.created_at) }}</td>
            <td>
              <span :class="['applicants__badge', `applicants__badge--${a.status}`]">
                {{ statusLabel(a.status) }}
              </span>
              <div v-if="a.status === 'rejected' && a.rejection_reason" class="applicants__reject-reason">
                거절 사유: {{ a.rejection_reason }}
              </div>
            </td>
            <td>
              <template v-if="a.status === 'pending'">
                <button class="applicants__btn applicants__btn--approve" @click="approve(a.id)">승인</button>
                <button class="applicants__btn applicants__btn--reject" @click="openRejectModal(a.id)">거절</button>
              </template>
              <span v-else class="applicants__decided">결정 완료</span>
            </td>
          </tr>
        </tbody>
      </table>
    </template>

    <!-- 거절 사유 모달 -->
    <div v-if="rejectModal.visible" class="applicants__overlay" @click.self="closeRejectModal">
      <div class="applicants__modal">
        <h2 class="applicants__modal-title">거절 사유 입력</h2>
        <p class="applicants__modal-desc">거절 사유는 신청자에게 전달됩니다.</p>
        <textarea
          v-model="rejectModal.reason"
          class="applicants__modal-textarea"
          rows="4"
          placeholder="거절 사유를 입력하세요."
        />
        <p v-if="actionError" class="applicants__action-error">{{ actionError }}</p>
        <div class="applicants__modal-actions">
          <button class="applicants__btn applicants__btn--reject" @click="submitReject">거절 확정</button>
          <button class="applicants__btn applicants__btn--cancel" @click="closeRejectModal">취소</button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.applicants {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px 16px;
}
.applicants__back {
  background: none;
  border: none;
  cursor: pointer;
  color: #555;
  font-size: 0.9rem;
  margin-bottom: 12px;
  padding: 0;
}
.applicants__back:hover { color: #222; }
.applicants__title {
  font-size: 1.4rem;
  font-weight: 700;
  margin-bottom: 20px;
}
.applicants__status {
  padding: 20px;
  text-align: center;
  color: #666;
}
.applicants__status--error { color: #c0392b; }
.applicants__action-error {
  color: #c0392b;
  margin-bottom: 12px;
  font-size: 0.9rem;
}
.applicants__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.applicants__table th,
.applicants__table td {
  padding: 10px 12px;
  border-bottom: 1px solid #eee;
  text-align: left;
  vertical-align: top;
}
.applicants__table th {
  background: #f5f5f5;
  font-weight: 600;
}
.applicants__motivation {
  max-width: 240px;
  white-space: pre-wrap;
  word-break: break-word;
}
.applicants__badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
}
.applicants__badge--pending { background: #f0f0f0; color: #555; }
.applicants__badge--approved { background: #d4edda; color: #155724; }
.applicants__badge--rejected { background: #f8d7da; color: #721c24; }
.applicants__reject-reason {
  font-size: 0.78rem;
  color: #721c24;
  margin-top: 4px;
  white-space: pre-wrap;
  word-break: break-word;
}
.applicants__btn {
  padding: 4px 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  margin-right: 4px;
}
.applicants__btn--approve { background: #28a745; color: #fff; }
.applicants__btn--approve:hover { background: #218838; }
.applicants__btn--reject { background: #dc3545; color: #fff; }
.applicants__btn--reject:hover { background: #c82333; }
.applicants__btn--cancel { background: #6c757d; color: #fff; }
.applicants__btn--cancel:hover { background: #5a6268; }
.applicants__decided { font-size: 0.82rem; color: #999; }

/* 모달 */
.applicants__overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.applicants__modal {
  background: #fff;
  border-radius: 8px;
  padding: 28px 24px;
  width: 420px;
  max-width: 90vw;
}
.applicants__modal-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 6px;
}
.applicants__modal-desc {
  font-size: 0.88rem;
  color: #555;
  margin-bottom: 14px;
}
.applicants__modal-textarea {
  width: 100%;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 8px;
  font-size: 0.9rem;
  resize: vertical;
  box-sizing: border-box;
}
.applicants__modal-actions {
  margin-top: 14px;
  display: flex;
  gap: 8px;
}
</style>
