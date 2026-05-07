/*
  请求级内存缓存：稳定的接口（课程类型 / 课程列表 / 教练列表 / 工作室配置等）
  在 5 分钟内不重复请求。仅 GET。

  用法：在 client.js 的 GET 拦截里检查 cacheableUrl(path)，命中直接返；
  写操作（POST/PATCH/DELETE）后调 invalidate(prefix) 清相关 key。
*/

const TTL = 5 * 60 * 1000   // 5 分钟
const cache = new Map()      // key -> { data, expireAt }

// 这些接口几乎不变，安全缓存
const CACHEABLE_PATTERNS = [
  /^\/courses(\?|$)/,
  /^\/admin\/courses(\?|$)/,
  /^\/coaches(\?|$)/,
  /^\/course-categories(\?|$)/,
  /^\/admin\/course-categories(\?|$)/,
  /^\/card-templates(\?|$)/,
  /^\/admin\/card-templates(\?|$)/,
  /^\/studio\/config$/,
  /^\/coaches\/\d+\/profile$/,
]

export function isCacheable(url) {
  return CACHEABLE_PATTERNS.some(re => re.test(url))
}

export function getCache(url) {
  const item = cache.get(url)
  if (!item) return null
  if (Date.now() > item.expireAt) { cache.delete(url); return null }
  return item.data
}

export function setCache(url, data) {
  cache.set(url, { data, expireAt: Date.now() + TTL })
}

export function invalidate(prefix) {
  for (const k of cache.keys()) {
    if (k.startsWith(prefix)) cache.delete(k)
  }
}

export function clearCache() { cache.clear() }
