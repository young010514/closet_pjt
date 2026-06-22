import api from './http'

const STORE_BASE = '/stores'

export const STORE_PAGE_SIZE = 20

export async function getStores(params = {}) {
  const response = await api.get(`${STORE_BASE}/`, {
    params,
  })

  return response.data
}

