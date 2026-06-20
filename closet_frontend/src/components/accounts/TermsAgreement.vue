<script setup>
import { computed, ref, watchEffect } from 'vue'

import FormFieldError from './FormFieldError.vue'

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
  },
  errors: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['update:modelValue'])
const allInput = ref(null)

const values = computed(() => ({
  service_terms_agreed: false,
  privacy_agreed: false,
  marketing_agreed: false,
  ...props.modelValue,
}))

const allChecked = computed(() =>
  values.value.service_terms_agreed && values.value.privacy_agreed && values.value.marketing_agreed,
)

const someChecked = computed(() =>
  values.value.service_terms_agreed || values.value.privacy_agreed || values.value.marketing_agreed,
)

watchEffect(() => {
  if (allInput.value) {
    allInput.value.indeterminate = someChecked.value && !allChecked.value
  }
})

function update(name, checked) {
  emit('update:modelValue', {
    ...values.value,
    [name]: checked,
  })
}

function updateAll(checked) {
  emit('update:modelValue', {
    service_terms_agreed: checked,
    privacy_agreed: checked,
    marketing_agreed: checked,
  })
}
</script>

<template>
  <fieldset class="form-section terms-box">
    <legend>약관 동의</legend>

    <label class="check-row check-row--all">
      <input
        ref="allInput"
        type="checkbox"
        :checked="allChecked"
        @change="updateAll($event.target.checked)"
      />
      <span>전체 동의</span>
    </label>

    <label class="check-row">
      <input
        type="checkbox"
        :checked="values.service_terms_agreed"
        @change="update('service_terms_agreed', $event.target.checked)"
      />
      <span>서비스 이용약관 동의 <strong>필수</strong></span>
    </label>
    <FormFieldError :errors="errors.service_terms_agreed" />

    <label class="check-row">
      <input
        type="checkbox"
        :checked="values.privacy_agreed"
        @change="update('privacy_agreed', $event.target.checked)"
      />
      <span>개인정보 수집 및 이용 동의 <strong>필수</strong></span>
    </label>
    <FormFieldError :errors="errors.privacy_agreed" />

    <label class="check-row">
      <input
        type="checkbox"
        :checked="values.marketing_agreed"
        @change="update('marketing_agreed', $event.target.checked)"
      />
      <span>마케팅 수신 동의 선택</span>
    </label>
    <FormFieldError :errors="errors.marketing_agreed" />
  </fieldset>
</template>
