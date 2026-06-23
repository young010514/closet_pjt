<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { normalizeApiError, searchUsers } from '@/api/accounts'
import StorePagination from '@/components/stores/StorePagination.vue'

const route = useRoute()
const router = useRouter()

const DEFAULT_PAGE_SIZE = 20

const searchInput = ref('')
const results = ref([])
const totalCount = ref(0)
const pageSize = ref(DEFAULT_PAGE_SIZE)
const currentPage = ref(1)
const isLoading = ref(false)
const errorMessage = ref('')

const searchTerm = computed(() => normalizeQueryValue(route.query.q))
const hasSearchTerm = computed(() => searchTerm.value.length > 0)
const pageCount = computed(() =>
  Math.max(1, Math.ceil(totalCount.value / Math.max(1, pageSize.value || 1))),
)

function normalizeQueryValue(value) {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

function normalizePageValue(value) {
  const raw = Array.isArray(value) ? value[0] : value
  const parsed = Number.parseInt(String(raw ?? ''), 10)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1
}

function formatCount(value) {
  return new Intl.NumberFormat('ko-KR').format(Number(value || 0))
}

function getAvatarLabel(user) {
  const nickname = (user?.nickname || '').trim()
  const username = (user?.username || '').trim()
  const base = nickname || username
  return base ? base.charAt(0).toUpperCase() : '?'
}

async function loadSearchResults() {
  errorMessage.value = ''
  results.value = []
  totalCount.value = 0
  pageSize.value = DEFAULT_PAGE_SIZE
  currentPage.value = normalizePageValue(route.query.page)

  if (!hasSearchTerm.value) {
    isLoading.value = false
    return
  }

  isLoading.value = true

  try {
    const data = await searchUsers({
      q: searchTerm.value,
      page: currentPage.value,
      page_size: DEFAULT_PAGE_SIZE,
    })

    results.value = Array.isArray(data.results) ? data.results : []
    totalCount.value = Number(data.count ?? 0)
    pageSize.value = Number(data.page_size ?? DEFAULT_PAGE_SIZE) || DEFAULT_PAGE_SIZE
    currentPage.value = Number(data.page ?? currentPage.value) || currentPage.value
  } catch (error) {
    const normalized = normalizeApiError(error)
    errorMessage.value =
      normalized.status === 404
        ? '검색 결과 페이지를 찾을 수 없습니다.'
        : normalized.message
  } finally {
    isLoading.value = false
  }
}

function submitSearch() {
  const nextTerm = searchInput.value.trim()
  if (!nextTerm) {
    return
  }

  router.push({
    name: 'user-search',
    query: { q: nextTerm },
  })
}

function goToPage(page) {
  if (!hasSearchTerm.value || page === currentPage.value) {
    return
  }

  router.push({
    name: 'user-search',
    query: {
      q: searchTerm.value,
      page,
    },
  })
}

watch(
  () => [route.query.q, route.query.page],
  () => {
    searchInput.value = searchTerm.value

    if (!hasSearchTerm.value) {
      results.value = []
      totalCount.value = 0
      pageSize.value = DEFAULT_PAGE_SIZE
      currentPage.value = 1
      errorMessage.value = ''
      isLoading.value = false
      return
    }

    loadSearchResults()
  },
  { immediate: true },
)
</script>

<template>
  <main class="page-view user-search-view">
    <section class="panel user-search-panel">
      <div class="user-search-hero">
        <p class="eyebrow">User Search</p>
        <h1>유저 검색</h1>
        <p class="muted-text">아이디 또는 닉네임으로 공개 프로필을 찾을 수 있습니다.</p>
      </div>

      <form class="user-search-form" @submit.prevent="submitSearch">
        <label class="sr-only" for="user-search-input">유저 검색</label>
        <input
          id="user-search-input"
          v-model="searchInput"
          type="search"
          placeholder="유저 검색"
          autocomplete="off"
        />
        <button type="submit" class="button button--primary" aria-label="유저 검색 실행">
          검색
        </button>
      </form>

      <div class="user-search-summary">
        <p v-if="!hasSearchTerm" class="muted-text">아이디 또는 닉네임을 입력해 검색해 주세요.</p>
        <p v-else class="muted-text">
          총 {{ formatCount(totalCount) }}명 검색됨
        </p>
      </div>

      <p v-if="isLoading" class="muted-text">검색 결과를 불러오는 중입니다.</p>
      <p v-else-if="errorMessage" class="alert alert--error">{{ errorMessage }}</p>
      <p v-else-if="hasSearchTerm && results.length === 0" class="muted-text">
        검색 결과가 없습니다.
      </p>

      <div v-else-if="hasSearchTerm" class="user-search-results">
        <RouterLink
          v-for="user in results"
          :key="user.id"
          class="user-search-card"
          :to="{ name: 'user-profile', params: { userId: user.id } }"
        >
          <div class="user-search-card__avatar" aria-hidden="true">
            <img
              v-if="user.profile_image"
              :src="user.profile_image"
              :alt="`${user.nickname || user.username} 프로필 이미지`"
            />
            <span v-else>{{ getAvatarLabel(user) }}</span>
          </div>

          <div class="user-search-card__body">
            <div class="user-search-card__title">
              <h2>{{ user.nickname || user.username }}</h2>
              <p>@{{ user.username }}</p>
            </div>

            <dl class="user-search-card__stats" aria-label="사용자 통계">
              <div>
                <dt>팔로워</dt>
                <dd>{{ formatCount(user.follower_count) }}</dd>
              </div>
              <div>
                <dt>팔로잉</dt>
                <dd>{{ formatCount(user.following_count) }}</dd>
              </div>
            </dl>
          </div>
        </RouterLink>
      </div>

      <StorePagination
        :page="currentPage"
        :page-count="pageCount"
        :is-loading="isLoading"
        aria-label="유저 검색 결과 페이지 이동"
        @change="goToPage"
      />
    </section>
  </main>
</template>

<style scoped>
.user-search-view {
  width: min(100%, 920px);
}

.user-search-panel {
  display: grid;
  gap: 1rem;
}

.user-search-hero {
  display: grid;
  gap: 0.35rem;
}

.user-search-form {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.user-search-form input {
  min-width: 0;
  flex: 1;
}

.user-search-summary {
  min-height: 1.5rem;
}

.user-search-results {
  display: grid;
  gap: 0.8rem;
}

.user-search-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.9rem;
  padding: 1rem;
  color: inherit;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  box-shadow: var(--shadow-panel);
  text-decoration: none;
  transition:
    transform 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.user-search-card:hover,
.user-search-card:focus-visible {
  transform: translateY(-1px);
  border-color: var(--color-accent);
  box-shadow: 0 18px 28px rgba(47, 125, 109, 0.14);
  outline: none;
}

.user-search-card__avatar {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-dark));
  border-radius: 18px;
}

.user-search-card__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-search-card__avatar span {
  font-size: 1.5rem;
  font-weight: 900;
}

.user-search-card__body {
  display: grid;
  gap: 0.8rem;
  min-width: 0;
}

.user-search-card__title {
  display: grid;
  gap: 0.1rem;
}

.user-search-card__title h2 {
  margin: 0;
  font-size: 1.05rem;
}

.user-search-card__title p {
  color: var(--color-text-muted);
  font-weight: 700;
}

.user-search-card__stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.user-search-card__stats div {
  padding: 0.75rem 0.85rem;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}

.user-search-card__stats dt {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.user-search-card__stats dd {
  margin: 0.2rem 0 0;
  color: var(--color-heading);
  font-size: 1.05rem;
  font-weight: 900;
}

@media (max-width: 640px) {
  .user-search-form {
    flex-direction: column;
    align-items: stretch;
  }

  .user-search-card {
    grid-template-columns: 1fr;
  }

  .user-search-card__avatar {
    width: 56px;
    height: 56px;
  }

  .user-search-card__stats {
    grid-template-columns: 1fr;
  }
}
</style>
