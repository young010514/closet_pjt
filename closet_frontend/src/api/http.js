import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  headers: {
    Accept: 'application/json',
  },
})

let csrfPromise = null

export async function initializeCsrf() {
  if (!csrfPromise) {
    csrfPromise = api.get('/accounts/csrf/').catch((error) => {
      csrfPromise = null
      throw error
    })
  }

  const response = await csrfPromise
  return response.data
}

export default api
