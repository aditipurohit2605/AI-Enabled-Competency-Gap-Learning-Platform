import { defineStore } from 'pinia'
import api from '@/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    user: (() => {
      try {
        const u = localStorage.getItem('user')
        return u ? JSON.parse(u) : null
      } catch {
        return null
      }
    })(),
    isLoading: false,
    error: null
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    role: (state) => state.user?.role || '',
    isLearner: (state) => state.user?.role === 'learner',
    isTrainer: (state) => state.user?.role === 'trainer',
    isAdmin: (state) => state.user?.role === 'admin',
    userName: (state) => state.user?.name || 'User'
  },

  actions: {
    async login(email, password) {
      this.isLoading = true
      this.error = null
      try {
        const res = await api.post('/auth/login', { email, password })
        this.token = res.token
        this.user = res.user
        localStorage.setItem('token', res.token)
        localStorage.setItem('user', JSON.stringify(res.user))
        return res
      } catch (err) {
        this.error = err.message
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async register(name, email, password, role = 'learner') {
      this.isLoading = true
      this.error = null
      try {
        const res = await api.post('/auth/register', { name, email, password, role })
        this.token = res.token
        this.user = res.user
        localStorage.setItem('token', res.token)
        localStorage.setItem('user', JSON.stringify(res.user))
        return res
      } catch (err) {
        this.error = err.message
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async fetchMe() {
      if (!this.token) return null
      try {
        const res = await api.get('/me')
        const userData = res.user || { id: res.id, name: res.name, role: res.role, email: res.email }
        this.user = userData
        localStorage.setItem('user', JSON.stringify(userData))
        return userData
      } catch {
        this.logout()
        return null
      }
    },

    logout() {
      this.token = null
      this.user = null
      this.error = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
  }
})
