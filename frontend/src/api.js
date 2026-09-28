import axios from 'axios'

// Create Axios client with base URL pointing to Flask backend or relative path
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor: attach Bearer token if present in localStorage
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: handle 401 Unauthorized by clearing session and redirecting
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response) {
      const status = error.response.status
      if (status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
          window.location.href = '/login'
        }
      }

      // Extract meaningful server error message
      const serverMessage = error.response.data?.message || error.response.data?.error
      const message = serverMessage || `Request failed with status ${status}`
      return Promise.reject(new Error(message))
    }

    if (error.request) {
      return Promise.reject(new Error('Network error: Unable to reach the server. Please check your backend connection.'))
    }

    return Promise.reject(error)
  }
)

export default api
