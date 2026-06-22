import api from './http'

const REGION_BASE = '/regions'

export async function getSidos() {
  const response = await api.get(`${REGION_BASE}/sidos/`)
  return response.data
}

export async function getSigungus(sido) {
  const response = await api.get(`${REGION_BASE}/sigungus/`, {
    params: { sido },
  })
  return response.data
}

export async function getDongs(sido, sigungu) {
  const response = await api.get(`${REGION_BASE}/dongs/`, {
    params: { sido, sigungu },
  })
  return response.data
}
