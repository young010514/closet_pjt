import { defineStore } from 'pinia'
import {
  createPost,
  deletePost,
  getPost,
  getPosts,
  likePost,
  updatePost,
} from '@/api/community'

export const useCommunityStore = defineStore('community', {
  state: () => ({
    posts: [],
    currentPost: null,
    isLoading: false,
    error: '',
  }),

  actions: {
    async fetchPosts(params = {}) {
      this.isLoading = true
      this.error = ''
      try {
        const res = await getPosts(params)
        this.posts = res.data
      } catch (e) {
        this.error = e.response?.data?.detail || '게시글을 불러오지 못했습니다.'
      } finally {
        this.isLoading = false
      }
    },

    async fetchPost(pk) {
      this.isLoading = true
      this.error = ''
      try {
        const res = await getPost(pk)
        this.currentPost = res.data
      } catch (e) {
        this.error = e.response?.data?.detail || '게시글을 불러오지 못했습니다.'
      } finally {
        this.isLoading = false
      }
    },

    async createPost(data) {
      const res = await createPost(data)
      return res.data
    },

    async updatePost(pk, data) {
      const res = await updatePost(pk, data)
      this.currentPost = res.data
      return res.data
    },

    async deletePost(pk) {
      await deletePost(pk)
      this.currentPost = null
    },

    async likePost(pk) {
      const res = await likePost(pk)
      if (this.currentPost?.id === pk) {
        this.currentPost.like_count = res.data.like_count
      }
      return res.data
    },
  },
})
