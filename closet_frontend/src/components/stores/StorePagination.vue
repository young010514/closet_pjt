<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: {
    type: Number,
    default: 1,
  },
  pageCount: {
    type: Number,
    default: 1,
  },
  isLoading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['change'])

const pageItems = computed(() => {
  const total = Math.max(1, props.pageCount)
  const current = Math.min(Math.max(props.page, 1), total)

  if (total <= 7) {
    return Array.from({ length: total }, (_, index) => index + 1)
  }

  const items = [1]
  let start = Math.max(2, current - 1)
  let end = Math.min(total - 1, current + 1)

  if (current <= 3) {
    start = 2
    end = 4
  } else if (current >= total - 2) {
    start = total - 3
    end = total - 1
  }

  if (start > 2) {
    items.push('ellipsis-start')
  }

  for (let page = start; page <= end; page += 1) {
    items.push(page)
  }

  if (end < total - 1) {
    items.push('ellipsis-end')
  }

  items.push(total)
  return items
})

function goTo(page) {
  if (props.isLoading || page < 1 || page > props.pageCount || page === props.page) {
    return
  }

  emit('change', page)
}
</script>

<template>
  <nav v-if="pageCount > 1" class="store-pagination" aria-label="옷가게 목록 페이지 이동">
    <button
      type="button"
      class="mini-button"
      :disabled="isLoading || page <= 1"
      @click="goTo(page - 1)"
    >
      이전
    </button>

    <div class="store-pagination__pages" aria-label="페이지 번호">
      <template v-for="item in pageItems" :key="item">
        <button
          v-if="typeof item === 'number'"
          type="button"
          :class="['mini-button', { 'mini-button--active': item === page }]"
          :disabled="isLoading || item === page"
          @click="goTo(item)"
        >
          {{ item }}
        </button>
        <span v-else class="store-pagination__ellipsis">…</span>
      </template>
    </div>

    <button
      type="button"
      class="mini-button"
      :disabled="isLoading || page >= pageCount"
      @click="goTo(page + 1)"
    >
      다음
    </button>
  </nav>
</template>

