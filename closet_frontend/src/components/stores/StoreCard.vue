<script setup>
import { computed } from 'vue'

const props = defineProps({
  store: {
    type: Object,
    required: true,
  },
})

const numberFormatter = new Intl.NumberFormat('ko-KR')

const displayName = computed(() => props.store?.display_name || props.store?.name || '-')
const branchName = computed(() => props.store?.branch_name || '')
const categoryName = computed(() => props.store?.category_name || '')
const regionLabel = computed(() => props.store?.region_label || '')
const address = computed(
  () => props.store?.address || props.store?.road_address || props.store?.jibun_address || '-',
)
const phone = computed(() => props.store?.phone || '')
const viewCount = computed(() =>
  numberFormatter.format(Number(props.store?.view_count ?? 0)),
)
</script>

<template>
  <article class="store-card">
    <div class="store-card__header">
      <div class="store-card__title">
        <h2 class="store-card__name">{{ displayName }}</h2>
        <p v-if="branchName" class="store-card__branch">{{ branchName }}</p>
      </div>

      <span class="store-chip">조회수 {{ viewCount }}</span>
    </div>

    <div class="store-card__meta">
      <span v-if="categoryName" class="store-chip">{{ categoryName }}</span>
      <span v-if="regionLabel" class="store-chip store-chip--ghost">{{ regionLabel }}</span>
    </div>

    <p class="store-card__address">{{ address }}</p>

    <div class="store-card__footer">
      <span v-if="phone">전화 {{ phone }}</span>
      <span>카카오맵 연동 준비중</span>
    </div>
  </article>
</template>

