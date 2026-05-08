import axios from 'axios'
import { isCacheable, getCache, setCache, invalidate, clearCache } from './cache.js'

const client = axios.create({ baseURL: '/api', timeout: 15000 })

// 自定义错误：保留 status / detail / 原始 url，方便业务层判断
export class ApiError extends Error {
  constructor(message, { status, detail, url, code } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.url = url
    this.code = code
  }
}

// 防止 401 时连续多次跳转
let redirectingToLogin = false

client.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

client.interceptors.response.use(
  (resp) => {
    const cfg = resp.config
    // GET + 可缓存：写缓存
    if (cfg.method === 'get' && isCacheable(cfg.url)) {
      setCache(cfg.url, resp.data)
    }
    // 写请求：让相关 GET 缓存失效
    if (['post', 'patch', 'delete', 'put'].includes(cfg.method)) {
      const url = cfg.url || ''
      if (url.includes('/courses') || url.includes('/course-categories')) invalidate('/courses')
      if (url.includes('/coaches')) invalidate('/coaches')
      if (url.includes('/card-templates') || url.includes('/admin/cards/'))
        invalidate('/card-templates')
      if (url.includes('/studio')) invalidate('/studio/config')
    }
    return resp.data
  },
  (err) => {
    const status = err?.response?.status
    const detail = err?.response?.data?.detail
    const url = err?.config?.url
    const code = err?.code

    // 友好消息：优先后端 detail，其次按状态码兜底
    let message = detail
    if (!message) {
      if (code === 'ECONNABORTED') message = '请求超时，请检查网络'
      else if (code === 'ERR_NETWORK') message = '网络异常，无法连接服务器'
      else if (status === 400) message = '请求参数有误'
      else if (status === 403) message = '没有权限执行此操作'
      else if (status === 404) message = '资源不存在'
      else if (status === 409) message = '操作冲突，请刷新后重试'
      else if (status === 422) message = '提交内容校验失败'
      else if (status === 429) message = '操作太频繁，请稍后再试'
      else if (status >= 500) message = '服务器开小差了，请稍后重试'
      else message = err.message || '未知错误'
    }

    // 401 → 清登录态、跳登录（避免重复跳）
    if (status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      clearCache()
      if (!redirectingToLogin && location.hash !== '#/login') {
        redirectingToLogin = true
        location.hash = '#/login'
        setTimeout(() => {
          redirectingToLogin = false
        }, 500)
      }
    }

    // 5xx：上报到 console.error，方便生产排查
    if (status >= 500) {
       
      console.error('[API 5xx]', url, status, detail || err.message)
    }

    return Promise.reject(new ApiError(message, { status, detail, url, code }))
  },
)

// 拦截 GET：先看缓存
const _origGet = client.get.bind(client)
client.get = function (url, config) {
  if (isCacheable(url)) {
    const cached = getCache(url)
    if (cached !== null) return Promise.resolve(cached)
  }
  return _origGet(url, config)
}

export default client
