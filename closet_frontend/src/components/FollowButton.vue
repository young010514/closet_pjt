<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { normalizeApiError, toggleFollow } from '@/api/accounts'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  targetUserId: {
    type: [Number, String],
    required: true,
  },
  initialIsFollowing: {
    type: Boolean,
    default: false,
  },
  initialFollowerCount: {
    type: Number,
    default: 0,
  },
  isMe: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['change'])

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const isFollowing = ref(false)
const followerCount = ref(0)
const isSubmitting = ref(false)
const message = ref('')

const buttonLabel = computed(() => (isFollowing.value ? '팔로잉' : '팔로우'))
const displayFollowerCount = computed(() =>
  new Intl.NumberFormat('ko-KR').format(followerCount.value),
)

function resetStateFromProps() {
  isFollowing.value = Boolean(props.initialIsFollowing)
  followerCount.value = Number(props.initialFollowerCount || 0)
  message.value = ''
}

watch(
  () => [props.targetUserId, props.initialIsFollowing, props.initialFollowerCount],
  resetStateFromProps,
  { immediate: true },
)

function goToLogin() {
  router.push({
    name: 'login',
    query: { redirect: route.fullPath },
  })
}

async function handleToggle() {
  if (props.isMe || !props.targetUserId || isSubmitting.value) return

  if (!authStore.isAuthenticated) {
    goToLogin()
    return
  }

  const previousState = {
    isFollowing: isFollowing.value,
    followerCount: followerCount.value,
  }

  isSubmitting.value = true
  message.value = ''

  isFollowing.value = !previousState.isFollowing
  followerCount.value = Math.max(
    0,
    previousState.followerCount + (previousState.isFollowing ? -1 : 1),
  )

  try {
    const result = await toggleFollow(props.targetUserId)
    isFollowing.value = Boolean(result.is_following)
    followerCount.value = Number(result.follower_count ?? followerCount.value)
    emit('change', {
      is_following: isFollowing.value,
      follower_count: followerCount.value,
      following_count: Number(result.following_count ?? 0),
    })
  } catch (error) {
    isFollowing.value = previousState.isFollowing
    followerCount.value = previousState.followerCount

    const normalized = normalizeApiError(error)
    if ([401, 403].includes(normalized.status)) {
      goToLogin()
      return
    }

    message.value = normalized.message
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div v-if="!isMe" class="follow-button-wrap">
    <button
      type="button"
      class="button follow-button"
      :class="isFollowing ? 'button--secondary' : 'button--primary'"
      :disabled="isSubmitting"
      :aria-pressed="isFollowing"
      @click="handleToggle"
    >
      <span>{{ buttonLabel }}</span>
      <span class="follow-button__count">{{ displayFollowerCount }}</span>
    </button>
    <p v-if="message" class="follow-button__message" role="alert">{{ message }}</p>
  </div>
</template>

<style scoped>
.follow-button-wrap {
  display: grid;
  justify-items: end;
  gap: 0.35rem;
  min-width: 0;
}

.follow-button {
  min-width: 120px;
  gap: 0.65rem;
  justify-content: space-between;
  white-space: nowrap;
}

.follow-button__count {
  font-size: 0.88rem;
  font-weight: 800;
  opacity: 0.9;
}

.follow-button__message {
  margin: 0;
  color: var(--color-danger);
  font-size: 0.78rem;
  font-weight: 700;
  text-align: right;
}
</style>
