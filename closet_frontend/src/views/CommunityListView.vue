<script setup>
import { onMounted, reactive, ref, computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useCommunityStore } from '@/stores/community'

const store = useCommunityStore()
const route = useRoute()

const VALID_BOARDS = ['fashion', 'daily', 'local_shop', 'experience']

const filters = reactive({
  board: VALID_BOARDS.includes(route.query.board) ? route.query.board : 'fashion',
  gender: '',
  category: '',
  ordering: 'latest',
})

const searchInput = ref('')
const appliedSearch = ref('')
const showSearch = computed(() => filters.board !== 'local_shop')

const BOARD_TABS = [
  { value: 'fashion', label: '패션 정보 공유' },
  { value: 'daily', label: '일상 & 소통' },
  { value: 'local_shop', label: '우리 동네 가게' },
  { value: 'experience', label: '체험단' },
]

const GENDER_OPTIONS = [
  { value: '', label: '성별 전체' },
  { value: 'male', label: '남성' },
  { value: 'female', label: '여성' },
  { value: 'kids', label: '키즈' },
]

const FASHION_CATEGORY_OPTIONS = [
  { value: '', label: '카테고리 전체' },
  { value: 'top', label: '상의' },
  { value: 'bottom', label: '하의' },
  { value: 'outer', label: '아우터' },
  { value: 'shoes', label: '슈즈' },
  { value: 'accessories', label: '잡화·악세사리' },
]

const DAILY_CATEGORY_OPTIONS = [
  { value: '', label: '전체' },
  { value: 'lifestyle', label: '라이프스타일' },
  { value: 'counseling', label: '고민·상담' },
]

const EXPERIENCE_CATEGORY_OPTIONS = [
  { value: '', label: '전체' },
  { value: 'recruit', label: '체험단 모집' },
  { value: 'review', label: '체험단 후기' },
]

const ORDERING_OPTIONS = [
  { value: 'latest', label: '최신순' },
  { value: 'popular', label: '인기순' },
  { value: 'viewed', label: '조회순' },
]

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

const EXPERIENCE_STATUS_LABEL = {
  recruiting: '모집중',
  closed: '마감',
  ended: '종료',
}

const EXPERIENCE_STATUS_CLASS = {
  recruiting: 'status-recruiting',
  closed: 'status-closed',
  ended: 'status-ended',
}

function selectBoard(value) {
  filters.board = value
  filters.gender = ''
  filters.category = ''
  if (value === 'local_shop') filters.ordering = 'latest'
  searchInput.value = ''
  appliedSearch.value = ''
  applyFilters()
}

function applyFilters() {
  const params = { board: filters.board }
  if (filters.gender) params.gender = filters.gender
  if (filters.category) params.category = filters.category
  if (filters.ordering) params.ordering = filters.ordering
  if (appliedSearch.value) params.search = appliedSearch.value
  store.fetchPosts(params)
}

function submitSearch() {
  appliedSearch.value = searchInput.value.trim()
  applyFilters()
}

function clearSearch() {
  searchInput.value = ''
  appliedSearch.value = ''
  applyFilters()
}

onMounted(() => applyFilters())
</script>

<template>
  <div class="community-list">
    <div class="list-header">
      <h2>커뮤니티</h2>
      <RouterLink class="btn-write" to="/community/new">글쓰기</RouterLink>
    </div>

    <!-- 상단 게시판 탭 -->
    <div class="board-tabs">
      <button
        v-for="tab in BOARD_TABS"
        :key="tab.value"
        class="board-tab"
        :class="{ active: filters.board === tab.value }"
        @click="selectBoard(tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 패션 정보 공유 선택 시 하위 필터 -->
    <div v-if="filters.board === 'fashion'" class="sub-filters">
      <div class="sub-filter-row">
        <button
          v-for="o in GENDER_OPTIONS"
          :key="o.value"
          class="filter-chip"
          :class="{ active: filters.gender === o.value }"
          @click="filters.gender = o.value; applyFilters()"
        >
          {{ o.label }}
        </button>
      </div>
      <div class="sub-filter-row">
        <button
          v-for="o in FASHION_CATEGORY_OPTIONS"
          :key="o.value"
          class="filter-chip"
          :class="{ active: filters.category === o.value }"
          @click="filters.category = o.value; applyFilters()"
        >
          {{ o.label }}
        </button>
      </div>
    </div>

    <!-- 일상 & 소통 선택 시 하위 필터 -->
    <div v-if="filters.board === 'daily'" class="sub-filters">
      <div class="sub-filter-row">
        <button
          v-for="o in DAILY_CATEGORY_OPTIONS"
          :key="o.value"
          class="filter-chip"
          :class="{ active: filters.category === o.value }"
          @click="filters.category = o.value; applyFilters()"
        >
          {{ o.label }}
        </button>
      </div>
    </div>

    <!-- 체험단 선택 시 하위 필터 -->
    <div v-if="filters.board === 'experience'" class="sub-filters">
      <div class="sub-filter-row">
        <button
          v-for="o in EXPERIENCE_CATEGORY_OPTIONS"
          :key="o.value"
          class="filter-chip"
          :class="{ active: filters.category === o.value }"
          @click="filters.category = o.value; applyFilters()"
        >
          {{ o.label }}
        </button>
      </div>
    </div>

    <!-- 정렬 -->
    <div v-if="filters.board !== 'local_shop'" class="ordering-row">
      <select v-model="filters.ordering" @change="applyFilters">
        <option v-for="o in ORDERING_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
    </div>

    <!-- 검색 -->
    <div v-if="showSearch" class="search-row">
      <div class="search-box">
        <input
          v-model="searchInput"
          type="text"
          class="search-input"
          placeholder="제목 또는 내용으로 검색"
          @keydown.enter="submitSearch"
        />
        <button v-if="searchInput" class="btn-search-clear" @click="clearSearch" aria-label="검색어 지우기">✕</button>
        <button class="btn-search" @click="submitSearch">검색</button>
      </div>
      <p v-if="appliedSearch" class="search-applied">
        "<strong>{{ appliedSearch }}</strong>" 검색 결과
        <button class="btn-search-reset" @click="clearSearch">전체 보기</button>
      </p>
    </div>

    <p v-if="store.isLoading">불러오는 중...</p>
    <p v-else-if="store.error" class="error">{{ store.error }}</p>
    <p v-else-if="store.posts.length === 0 && appliedSearch">
      "<strong>{{ appliedSearch }}</strong>"에 대한 검색 결과가 없습니다.
    </p>
    <p v-else-if="store.posts.length === 0">게시글이 없습니다.</p>

    <ul v-else class="post-list">
      <li v-for="post in store.posts" :key="post.id" class="post-item">
        <RouterLink :to="`/community/${post.id}`" class="post-link">
          <div class="post-meta">
            <span class="badge board-badge">{{ BOARD_LABEL[post.board] ?? post.board }}</span>
            <span v-if="post.category" class="badge">{{ CATEGORY_LABEL[post.category] ?? post.category }}</span>
            <span
              v-if="post.experience_status"
              class="badge status-badge"
              :class="EXPERIENCE_STATUS_CLASS[post.experience_status]"
            >
              {{ EXPERIENCE_STATUS_LABEL[post.experience_status] }}
            </span>
          </div>
          <p class="post-title">{{ post.title }}</p>
          <div class="post-info">
            <span>{{ post.author_name }}</span>
            <span>조회 {{ post.view_count }}</span>
            <span>좋아요 {{ post.like_count }}</span>
          </div>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.community-list { max-width: 800px; margin: 0 auto; padding: 1rem; }

.list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.2rem; }
.btn-write { padding: 0.4rem 1rem; background: #333; color: #fff; border-radius: 4px; text-decoration: none; }

/* 게시판 탭 */
.board-tabs {
  display: flex;
  border-bottom: 2px solid #eee;
  margin-bottom: 0;
}
.board-tab {
  flex: 1;
  padding: 0.7rem 0.5rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  font-size: 0.95rem;
  color: #666;
  transition: color 0.15s, border-color 0.15s;
}
.board-tab:hover { color: #333; }
.board-tab.active { color: #333; border-bottom-color: #333; font-weight: 600; }

/* 하위 필터 */
.sub-filters {
  background: #f8f8f8;
  border: 1px solid #eee;
  border-top: none;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.sub-filter-row { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.filter-chip {
  padding: 0.3rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 20px;
  background: #fff;
  font-size: 0.82rem;
  cursor: pointer;
  color: #555;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.filter-chip:hover { border-color: #999; }
.filter-chip.active { background: #333; color: #fff; border-color: #333; }

/* 정렬 */
.ordering-row {
  display: flex;
  justify-content: flex-end;
  margin: 0.75rem 0;
}
.ordering-row select { padding: 0.3rem 0.5rem; border: 1px solid #ccc; border-radius: 4px; font-size: 0.85rem; }

/* 검색 */
.search-row { margin: 0.5rem 0 0.75rem; display: flex; flex-direction: column; gap: 0.4rem; }
.search-box { display: flex; gap: 0; border: 1px solid #ccc; border-radius: 6px; overflow: hidden; }
.search-input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: none;
  outline: none;
  font-size: 0.9rem;
}
.btn-search-clear {
  background: none;
  border: none;
  padding: 0 0.5rem;
  cursor: pointer;
  color: #aaa;
  font-size: 0.85rem;
}
.btn-search-clear:hover { color: #555; }
.btn-search {
  padding: 0.5rem 1rem;
  background: #333;
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 0.88rem;
  font-weight: 600;
  white-space: nowrap;
}
.btn-search:hover { background: #111; }
.search-applied { font-size: 0.85rem; color: #555; display: flex; align-items: center; gap: 0.5rem; }
.btn-search-reset {
  background: none;
  border: none;
  color: #3c5fbe;
  cursor: pointer;
  font-size: 0.82rem;
  text-decoration: underline;
  padding: 0;
}

/* 게시글 목록 */
.post-list { list-style: none; padding: 0; }
.post-item { border-bottom: 1px solid #eee; }
.post-link { display: block; padding: 0.8rem 0; text-decoration: none; color: inherit; }
.post-link:hover { background: #f9f9f9; }
.post-meta { display: flex; gap: 0.4rem; margin-bottom: 0.3rem; align-items: center; }
.badge { font-size: 0.75rem; padding: 0.1rem 0.4rem; background: #eee; border-radius: 3px; }
.board-badge { background: #e8f0fe; color: #3c5fbe; }
.status-badge { font-weight: 600; }
.status-recruiting { background: #e6f4ea; color: #1e7e34; }
.status-closed { background: #fff3cd; color: #856404; }
.status-ended { background: #f8d7da; color: #721c24; }
.post-title { font-size: 1rem; font-weight: 500; margin-bottom: 0.3rem; }
.post-info { display: flex; gap: 1rem; font-size: 0.8rem; color: #888; }
.error { color: red; }
</style>
