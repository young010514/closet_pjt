import api from './http'

const PERSONAL_COLOR_BASE = '/personal-color/analyses'

const ERROR_MESSAGE_MAP = {
  image_required: '이미지 파일을 선택해 주세요.',
  unsupported_image_type: 'JPEG, PNG, WEBP 이미지 파일만 업로드할 수 있습니다.',
  image_type_mismatch: '파일 확장자와 MIME 형식이 일치하지 않습니다.',
  file_too_large: '파일 크기는 10MB 이하여야 합니다.',
  corrupted_image: '손상된 이미지 파일입니다.',
  invalid_image: '이미지 파일을 읽을 수 없습니다.',
  image_too_small: '이미지 크기는 최소 256 x 256이어야 합니다.',
  image_too_large: '이미지 크기는 최대 4096 x 4096을 초과할 수 없습니다.',
  face_not_detected: '얼굴을 찾을 수 없습니다. 얼굴이 정면에 보이는 사진을 사용해 주세요.',
  analysis_provider_unavailable: 'AI 분석 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.',
  analysis_result_invalid: '분석 결과 형식이 올바르지 않습니다.',
  analysis_failed: '분석 중 오류가 발생했습니다.',
  not_authenticated: '로그인이 필요합니다.',
  analysis_not_found: '기록을 찾을 수 없습니다.',
}

function flattenMessage(value) {
  if (value === null || value === undefined || value === '') return ''

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }

  if (Array.isArray(value)) {
    return flattenMessage(value[0])
  }

  if (typeof value === 'object') {
    const firstValue = Object.values(value)[0]
    return flattenMessage(firstValue)
  }

  return String(value)
}

function readErrorResponse(error) {
  const status = error?.response?.status ?? null
  const data = error?.response?.data

  const code = typeof data?.code === 'string' ? data.code : ''
  const detail = flattenMessage(data?.detail || data?.message || data)

  return {
    status,
    code,
    detail,
    raw: data,
  }
}

export function normalizePersonalColorError(error) {
  const { status, code, detail, raw } = readErrorResponse(error)

  if (!error?.response) {
    return {
      status: null,
      code: 'network_error',
      detail: '',
      message: '서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.',
      raw: null,
    }
  }

  if ([401, 403].includes(status)) {
    return {
      status,
      code: 'session_expired',
      detail,
      message: '로그인이 만료되었습니다. 다시 로그인해 주세요.',
      raw,
    }
  }

  if (status === 404) {
    return {
      status,
      code: code || 'analysis_not_found',
      detail,
      message: ERROR_MESSAGE_MAP.analysis_not_found,
      raw,
    }
  }

  if (code && ERROR_MESSAGE_MAP[code]) {
    return {
      status,
      code,
      detail,
      message: ERROR_MESSAGE_MAP[code],
      raw,
    }
  }

  if (detail) {
    return {
      status,
      code: code || 'analysis_error',
      detail,
      message: detail,
      raw,
    }
  }

  return {
    status,
    code: code || 'analysis_error',
    detail: '',
    message: '요청을 처리하지 못했습니다.',
    raw,
  }
}

export async function createPersonalColorAnalysis(imageFile) {
  const formData = new FormData()
  formData.append('image', imageFile)

  const response = await api.post(`${PERSONAL_COLOR_BASE}/`, formData)
  return response.data
}

export async function getPersonalColorAnalyses(params = {}) {
  const response = await api.get(`${PERSONAL_COLOR_BASE}/`, { params })
  return response.data
}

export async function getPersonalColorAnalysis(id) {
  const response = await api.get(`${PERSONAL_COLOR_BASE}/${id}/`)
  return response.data
}

export async function deletePersonalColorAnalysis(id) {
  const response = await api.delete(`${PERSONAL_COLOR_BASE}/${id}/`)
  return response.data
}
