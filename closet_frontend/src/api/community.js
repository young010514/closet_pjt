import api from './http'

function buildFormData(data) {
  const fd = new FormData()
  for (const [key, val] of Object.entries(data)) {
    if (key === 'images') {
      for (const file of val) fd.append('images', file)
    } else if (key === 'videos') {
      for (const file of val) fd.append('videos', file)
    } else if (key === 'hashtags' && Array.isArray(val)) {
      fd.append(key, JSON.stringify(val))
    } else if (val !== null && val !== undefined) {
      fd.append(key, val)
    }
  }
  return fd
}

const hasFiles = (data) =>
  (Array.isArray(data.images) && data.images.length > 0) ||
  (Array.isArray(data.videos) && data.videos.length > 0)

export const getPosts = (params = {}) => api.get('/community/posts/', { params })

export const getPost = (pk) => api.get(`/community/posts/${pk}/`)

export const createPost = (data) => {
  if (hasFiles(data)) {
    return api.post('/community/posts/', buildFormData(data))
  }
  return api.post('/community/posts/', data)
}

export const updatePost = (pk, data) => {
  if (hasFiles(data)) {
    return api.put(`/community/posts/${pk}/`, buildFormData(data))
  }
  return api.put(`/community/posts/${pk}/`, data)
}

export const deletePost = (pk) => api.delete(`/community/posts/${pk}/`)

export const likePost = (pk) => api.post(`/community/posts/${pk}/like/`)

export const checkApplication = (pk) => api.get(`/community/posts/${pk}/apply/`)

export const submitApplication = (pk, data) => api.post(`/community/posts/${pk}/apply/`, data)

export const fetchComments = (pk) => api.get(`/community/posts/${pk}/comments/`)

export const createComment = (pk, data) => api.post(`/community/posts/${pk}/comments/`, data)

export const updateComment = (pk, commentPk, data) => api.put(`/community/posts/${pk}/comments/${commentPk}/`, data)

export const deleteComment = (pk, commentPk) => api.delete(`/community/posts/${pk}/comments/${commentPk}/`)