import { defineStore } from 'pinia'
import {
  createPost,
  deletePost,
  getPost,
  getPosts,
  likePost as toggleLikePost,
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
      const res = await toggleLikePost(pk)
      const payload = res.data
      const postId = Number(pk)

      if (this.currentPost && Number(this.currentPost.id) === postId) {
        this.currentPost = {
          ...this.currentPost,
          like_count: payload.like_count,
          is_liked: payload.is_liked,
        }
      }

      this.posts = this.posts.map((post) =>
        Number(post.id) === postId
          ? {
              ...post,
              like_count: payload.like_count,
              is_liked: payload.is_liked,
            }
          : post,
      )

      return payload
    },
  },
})
