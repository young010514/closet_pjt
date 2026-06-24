<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const images = [
  '/landing1.jpg',
  '/landing2.jpg',
  '/landing3.jpg',
  '/landing4.jpg',
  '/landing5.jpg',
]

const current = ref(0)
let timer = null

function prev() {
  current.value = (current.value - 1 + images.length) % images.length
  resetTimer()
}

function next() {
  current.value = (current.value + 1) % images.length
  resetTimer()
}

function goTo(index) {
  current.value = index
  resetTimer()
}

function resetTimer() {
  clearInterval(timer)
  timer = setInterval(() => {
    current.value = (current.value + 1) % images.length
  }, 4000)
}

onMounted(() => {
  resetTimer()
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<template>
  <div class="landing">
    <img
      v-for="(img, i) in images"
      :key="i"
      :src="img"
      :class="['slider__img', { 'slider__img--active': i === current }]"
      alt="랜딩 이미지"
    />

    <button class="slider__btn slider__btn--prev" @click="prev" aria-label="이전">&#8249;</button>
    <button class="slider__btn slider__btn--next" @click="next" aria-label="다음">&#8250;</button>

    <div class="slider__dots">
      <button
        v-for="(_, i) in images"
        :key="i"
        :class="['dot', { 'dot--active': i === current }]"
        @click="goTo(i)"
        :aria-label="`${i + 1}번째 이미지`"
      />
    </div>
  </div>
</template>

<style scoped>
.landing {
  position: relative;
  width: 100%;
  height: calc(100vh - 56px);
  overflow: hidden;
  background: #111;
}

.slider__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 0.4s ease;
}

.slider__img--active {
  opacity: 1;
}

.slider__btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  border: none;
  border-radius: 50%;
  width: 52px;
  height: 52px;
  font-size: 2rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.slider__btn:hover {
  background: rgba(0, 0, 0, 0.7);
}

.slider__btn--prev {
  left: 20px;
}

.slider__btn--next {
  right: 20px;
}

.slider__dots {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  display: flex;
  gap: 10px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #fff;
  background: transparent;
  cursor: pointer;
  padding: 0;
  transition: background 0.2s;
}

.dot--active {
  background: #fff;
}
</style>
