import { defineStore } from 'pinia'
import api from '../api/client'

export const useAuth = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isAdmin: (s) => s.user?.role === 'admin',
    isStaff: (s) => ['admin', 'staff'].includes(s.user?.role),
    isCoach: (s) => s.user?.role === 'coach',
    isMember: (s) => s.user?.role === 'member',
  },
  actions: {
    async login(phone, password) {
      const data = await api.post('/auth/login', { phone, password })
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('token', this.token)
      localStorage.setItem('user', JSON.stringify(this.user))
      return data.user
    },
    async register(phone, password, name) {
      const data = await api.post('/auth/register', { phone, password, name })
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('token', this.token)
      localStorage.setItem('user', JSON.stringify(this.user))
      return data.user
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
  },
})
