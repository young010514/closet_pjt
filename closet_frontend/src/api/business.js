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

export function getExperiencePosts(ordering = 'latest') {
  return http.get('/business/experience/posts/', { params: { ordering } }).then((r) => r.data)
}
export function createExperiencePost(formData) {
  return http.post('/business/experience/posts/', formData).then((r) => r.data)
}
export function getExperiencePost(pk) {
  return http.get(`/business/experience/posts/${pk}/`).then((r) => r.data)
}
export function updateExperiencePost(pk, formData) {
  return http.put(`/business/experience/posts/${pk}/`, formData).then((r) => r.data)
}
export function deleteExperiencePost(pk) {
  return http.delete(`/business/experience/posts/${pk}/`).then((r) => r.data)
}
export function getExperienceApplicants(pk) {
  return http.get(`/business/experience/posts/${pk}/applicants/`).then((r) => r.data)
}

export function decideApplicant(postPk, applicationId, data) {
  return http.patch(`/business/experience/posts/${postPk}/applicants/${applicationId}/decision/`, data).then((r) => r.data)
}
