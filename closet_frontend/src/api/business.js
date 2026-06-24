import http from './http'

export function getDashboard() {
  return http.get('/business/dashboard/').then((r) => r.data)
}

export function getStorePosts(ordering = 'latest') {
  return http.get('/business/store/posts/', { params: { ordering } }).then((r) => r.data)
}

export function createStorePost(formData) {
  return http.post('/business/store/posts/', formData).then((r) => r.data)
}

export function getStorePost(pk) {
  return http.get(`/business/store/posts/${pk}/`).then((r) => r.data)
}

export function updateStorePost(pk, formData) {
  return http.put(`/business/store/posts/${pk}/`, formData).then((r) => r.data)
}

export function deleteStorePost(pk) {
  return http.delete(`/business/store/posts/${pk}/`).then((r) => r.data)
}
