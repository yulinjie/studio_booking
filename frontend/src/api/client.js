import axios from 'axios'
import { isCacheable, getCache, setCache, invalidate, clearCache } from './cache.js'

const client = axios.create({ baseURL: '/api', timeout: 15000 })

client.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

client.interceptors.response.use(
  (resp) => {
    // GET + 可缓存路径：缓存数据
    const cfg = resp.config
    if (cfg.method === 'get' && isCacheable(cfg.url)) {
      setCache(cfg.url, resp.data)
    }
    // 写请求：让相关 GET 缓存失效
    if (['post', 'patch', 'delete', 'put'].includes(cfg.method)) {
      const url = cfg.url || ''
      if (url.includes('/courses') || url.includes('/course-categories')) invalidate('/courses')
      if (url.includes('/coaches')) invalidate('/coaches')
      if (url.includes('/card-templates') || url.includes('/admin/cards/')) invalidate('/card-templates')
      if (url.includes('/studio')) invalidate('/studio/config')
    }
    return resp.data
  },
  (err) => {
    const detail = err?.response?.data?.detail || err.message || '网络错误'
    if (err?.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      clearCache()
      if (location.hash !== '#/login') location.hash = '#/login'
    }
    return Promise.reject(new Error(detail))
  },
)

// 拦截 GET 请求，先看缓存
const _origGet = client.get.bind(client)
client.get = function(url, config) {
  if (isCacheable(url)) {
    const cached = getCache(url)
    if (cached !== null) return Promise.resolve(cached)
  }
  return _origGet(url, config)
}

export default client
