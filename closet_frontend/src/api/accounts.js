import api, { initializeCsrf } from './http'

const ACCOUNT_BASE = '/accounts'

export async function getSignupTypes() {
  const response = await api.get(`${ACCOUNT_BASE}/signup/`)
  return response.data
}

export async function signupNormal(payload) {
  await initializeCsrf()
  const response = await api.post(`${ACCOUNT_BASE}/signup/normal/`, payload)
  return response.data
}

export async function signupBusiness(payload) {
  await initializeCsrf()
  const response = await api.post(`${ACCOUNT_BASE}/signup/business/`, payload)
  return response.data
}

export async function login(payload) {
  await initializeCsrf()
  const response = await api.post(`${ACCOUNT_BASE}/login/`, payload)
  return response.data
}

export async function logout() {
  await initializeCsrf()
  const response = await api.post(`${ACCOUNT_BASE}/logout/`)
  return response.data
}

export async function getCurrentUser() {
  const response = await api.get(`${ACCOUNT_BASE}/mypage/`)
  return response.data
}

export async function getUserProfile(userId) {
  const response = await api.get(`${ACCOUNT_BASE}/users/${userId}/`)
  return response.data
}

export async function searchUsers(params) {
  const response = await api.get(`${ACCOUNT_BASE}/users/search/`, {
    params,
  })
  return response.data
}

export async function updateMyProfile(payload) {
  await initializeCsrf()
  const response = await api.patch(`${ACCOUNT_BASE}/me/profile/`, payload)
  return response.data
}

export async function updateMyBusinessProfile(payload) {
  await initializeCsrf()
  const response = await api.patch(`${ACCOUNT_BASE}/me/business-profile/`, payload)
  return response.data
}

export async function getMyRegions() {
  const response = await api.get(`${ACCOUNT_BASE}/me/regions/`)
  return response.data
}

export async function updateMyRegions(regionIds) {
  await initializeCsrf()
  const response = await api.put(`${ACCOUNT_BASE}/me/regions/`, {
    region_ids: regionIds,
  })
  return response.data
}

export async function reorderRegions(regionIds) {
  return updateMyRegions(regionIds)
}

export async function toggleFollow(userId) {
  await initializeCsrf()
  const response = await api.post(`${ACCOUNT_BASE}/users/${userId}/follow/`)
  return response.data
}

export async function getFollowers(userId) {
  const response = await api.get(`${ACCOUNT_BASE}/users/${userId}/followers/`)
  return response.data
}

export async function getFollowing(userId) {
  const response = await api.get(`${ACCOUNT_BASE}/users/${userId}/following/`)
  return response.data
}

export function normalizeApiError(error) {
  const status = error?.response?.status ?? null
  const data = error?.response?.data
  const fieldErrors = {}
  const formErrors = []

  if (!error?.response) {
    formErrors.push('서버에 연결할 수 없습니다. Django 서버가 실행 중인지 확인해 주세요.')
  } else if (!data) {
    formErrors.push('서버 응답을 읽을 수 없습니다.')
  } else if (typeof data === 'string') {
    formErrors.push(data)
  } else if (Array.isArray(data)) {
    formErrors.push(...flattenMessages(data))
  } else if (typeof data === 'object') {
    Object.entries(data).forEach(([key, value]) => {
      const messages = flattenMessages(value)
      if (!messages.length) return

      if (key === 'detail' || key === 'non_field_errors') {
        formErrors.push(...messages)
        return
      }

      fieldErrors[key] = messages
    })
  }

  if (status === 409 && !formErrors.length) {
    formErrors.push('이미 사용 중인 회원 정보가 있습니다.')
  }

  if (!formErrors.length && !Object.keys(fieldErrors).length) {
    formErrors.push('요청을 처리하지 못했습니다.')
  }

  return {
    status,
    fieldErrors,
    formErrors,
    message: formErrors[0] || '입력 내용을 확인해 주세요.',
    raw: data,
  }
}

function flattenMessages(value, path = '') {
  if (value === null || value === undefined || value === '') return []

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return [String(value)]
  }

  if (Array.isArray(value)) {
    return value.flatMap((item, index) => flattenMessages(item, path ? `${path}.${index}` : String(index)))
  }

  if (typeof value === 'object') {
    return Object.entries(value).flatMap(([key, nested]) => {
      const nestedPath = path ? `${path}.${key}` : key
      return flattenMessages(nested, nestedPath).map((message) =>
        path || typeof nested === 'object' ? `${nestedPath}: ${message}` : message,
      )
    })
  }

  return [String(value)]
}
