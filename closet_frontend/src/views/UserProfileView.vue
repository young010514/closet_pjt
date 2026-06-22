<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { getUserProfile, normalizeApiError } from '@/api/accounts'
import { getPosts } from '@/api/community'
import FollowButton from '@/components/FollowButton.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()

const profile = ref(null)
const posts = ref([])
const isLoadingProfile = ref(false)
const isLoadingPosts = ref(false)
const profileError = ref('')
const postsError = ref('')

const BOARD_LABELS = {
  fashion: '패션',
  daily: '일상',
  local_shop: '로컬 샵',
  experience: '체험단',
}

const userId = computed(() => Number(route.params.userId))
const isMe = computed(() => Boolean(profile.value && authStore.user?.id === profile.value.id))
const displayName = computed(() => profile.value?.nickname || profile.value?.username || '사용자')
const displayUsername = computed(() => (profile.value?.username ? `@${profile.value.username}` : ''))
const avatarLetter = computed(() => (displayName.value ? displayName.value.trim().charAt(0) : '?'))

function formatCount(value) {
  return new Intl.NumberFormat('ko-KR').format(Number(value || 0))
}

function formatDate(value) {
  if (!value) return '-'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

function boardLabel(board) {
  return BOARD_LABELS[board] || board || '게시글'
}

async function loadProfile(targetUserId) {
  profileError.value = ''
  postsError.value = ''
  profile.value = null
  posts.value = []

  if (!Number.isInteger(targetUserId) || targetUserId < 1) {
    profileError.value = '잘못된 사용자 주소입니다.'
    return
  }

  isLoadingProfile.value = true

  try {
    profile.value = await getUserProfile(targetUserId)
  } catch (error) {
    const normalized = normalizeApiError(error)
    profileError.value =
      normalized.status === 404 ? '존재하지 않는 사용자입니다.' : normalized.message
    return
  } finally {
    isLoadingProfile.value = false
  }

  isLoadingPosts.value = true
  try {
    const response = await getPosts({ author: targetUserId })
    const data = response.data

    posts.value = Array.isArray(data)
      ? data
      : Array.isArray(data.results)
        ? data.results
        : []
  } catch (error) {
    const normalized = normalizeApiError(error)
    postsError.value = normalized.message
  } finally {
    isLoadingPosts.value = false
  }
}

function handleFollowChange(payload) {
  if (!profile.value) return

  profile.value = {
    ...profile.value,
    ...payload,
  }
}

watch(userId, (value) => {
  loadProfile(value)
}, { immediate: true })
</script>

<template>
  <main class="page-view profile-view">
    <section class="panel profile-hero">
      <div v-if="isLoadingProfile" class="profile-state">
        <p class="muted-text">프로필을 불러오는 중입니다.</p>
      </div>

      <template v-else-if="profile">
        <div class="profile-hero__main">
          <div class="profile-avatar" aria-hidden="true">
            <span>{{ avatarLetter }}</span>
          </div>

          <div class="profile-copy">
            <p class="eyebrow">Public Profile</p>
            <h1>{{ displayName }}</h1>
            <p class="profile-username">{{ displayUsername }}</p>
          </div>
        </div>

        <div class="profile-hero__actions">
          <RouterLink v-if="isMe" class="button button--secondary" to="/mypage">
            마이페이지
          </RouterLink>
          <FollowButton
            v-else
            :target-user-id="profile.id"
            :initial-is-following="profile.is_following"
            :initial-follower-count="profile.follower_count"
            :is-me="isMe"
            @change="handleFollowChange"
          />
        </div>

        <dl class="profile-stats" aria-label="프로필 요약">
          <div class="profile-stat">
            <dt>팔로워</dt>
            <dd>{{ formatCount(profile.follower_count) }}</dd>
          </div>
          <div class="profile-stat">
            <dt>팔로잉</dt>
            <dd>{{ formatCount(profile.following_count) }}</dd>
          </div>
          <div class="profile-stat">
            <dt>게시글</dt>
            <dd>{{ formatCount(posts.length) }}</dd>
          </div>
        </dl>
      </template>

      <div v-else class="profile-state">
        <p class="alert alert--error">{{ profileError || '프로필을 찾을 수 없습니다.' }}</p>
        <RouterLink class="button button--secondary" to="/community">커뮤니티로 돌아가기</RouterLink>
      </div>
    </section>

    <section v-if="profile" class="panel profile-posts">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Posts</p>
          <h2>작성한 게시글</h2>
        </div>
        <span class="muted-text">{{ formatCount(posts.length) }}개</span>
      </div>

      <p v-if="postsError" class="alert alert--error">{{ postsError }}</p>
      <p v-else-if="isLoadingPosts" class="muted-text">게시글을 불러오는 중입니다.</p>
      <p v-else-if="posts.length === 0" class="muted-text">아직 작성한 게시글이 없습니다.</p>

      <ul v-else class="profile-post-list">
        <li v-for="post in posts" :key="post.id" class="profile-post-item">
          <RouterLink class="profile-post-link" :to="{ name: 'community-detail', params: { pk: post.id } }">
            <div class="profile-post-top">
              <span class="profile-post-board">{{ boardLabel(post.board) }}</span>
              <span class="profile-post-date">{{ formatDate(post.created_at) }}</span>
            </div>
            <h3>{{ post.title }}</h3>
            <p class="profile-post-meta">
              조회 {{ formatCount(post.view_count) }} · 좋아요 {{ formatCount(post.like_count) }}
            </p>
          </RouterLink>
        </li>
      </ul>
    </section>
  </main>
</template>

<style scoped>
.profile-view {
  display: grid;
  gap: 1rem;
}

.profile-hero {
  display: grid;
  gap: 1.25rem;
  background:
    radial-gradient(circle at top right, rgba(47, 125, 109, 0.14), transparent 34%),
    linear-gradient(135deg, rgba(47, 125, 109, 0.08), rgba(255, 255, 255, 0.98));
}

.profile-state {
  display: grid;
  gap: 0.75rem;
  justify-items: start;
}

.profile-hero__main {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 1rem;
  align-items: center;
}

.profile-avatar {
  display: grid;
  place-items: center;
  width: 76px;
  height: 76px;
  color: #fff;
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-dark));
  border-radius: 24px;
  box-shadow: 0 16px 30px rgba(47, 125, 109, 0.18);
}

.profile-avatar span {
  font-size: 1.9rem;
  font-weight: 900;
}

.profile-copy {
  display: grid;
  gap: 0.25rem;
}

.profile-copy h1 {
  margin: 0;
}

.profile-username {
  margin: 0;
  color: var(--color-text-muted);
  font-weight: 700;
}

.profile-hero__actions {
  display: flex;
  justify-content: flex-end;
}

.profile-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}

.profile-stat {
  padding: 0.9rem 1rem;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}

.profile-stat dt {
  color: var(--color-text-muted);
  font-size: 0.82rem;
}

.profile-stat dd {
  margin: 0.2rem 0 0;
  color: var(--color-heading);
  font-size: 1.45rem;
  font-weight: 900;
}

.profile-posts {
  display: grid;
  gap: 1rem;
}

.profile-post-list {
  display: grid;
  gap: 0.75rem;
  padding: 0;
  list-style: none;
}

.profile-post-item {
  border: 1px solid var(--color-border);
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
  box-shadow: var(--shadow-panel);
}

.profile-post-link {
  display: grid;
  gap: 0.45rem;
  padding: 1rem 1.05rem;
  color: inherit;
  text-decoration: none;
}

.profile-post-link:hover {
  background: var(--color-surface-muted);
}

.profile-post-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.profile-post-board {
  color: var(--color-accent-dark);
  font-size: 0.82rem;
  font-weight: 800;
}

.profile-post-date {
  color: var(--color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.profile-post-link h3 {
  margin: 0;
  color: var(--color-heading);
  font-size: 1.02rem;
  line-height: 1.45;
}

.profile-post-meta {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.86rem;
  font-weight: 700;
}

@media (max-width: 640px) {
  .profile-hero__main {
    grid-template-columns: 1fr;
    justify-items: start;
  }

  .profile-hero__actions {
    justify-content: flex-start;
  }

  .profile-stats {
    grid-template-columns: 1fr;
  }

  .profile-avatar {
    width: 64px;
    height: 64px;
    border-radius: 20px;
  }
}
</style>
