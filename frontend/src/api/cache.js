/*
  请求级内存缓存。

  设计原则（2026-05 修订）：
  - 只缓存 H5 会员端读多写少、变动不频繁的接口
  - admin 后台一律不缓存（写操作多，缓存收益小，缓存失效逻辑容易出 bug）
  - 写操作发生时统一 clearCache() 兜底，避免精细 invalidate 写错
*/

const FIVE_MIN = 5 * 60 * 1000
const HALF_HOUR = 30 * 60 * 1000
const ONE_HOUR = 60 * 60 * 1000

// 仅缓存 H5 公开接口（不带 /admin/ 前缀）
const CACHE_RULES = [
  { match: /^\/studio\/config$/, ttl: ONE_HOUR },
  { match: /^\/courses(\?|$)/, ttl: HALF_HOUR },
  { match: /^\/coaches(\?|$)/, ttl: HALF_HOUR },
  { match: /^\/coaches\/\d+\/profile$/, ttl: HALF_HOUR },
  { match: /^\/course-categories(\?|$)/, ttl: HALF_HOUR },
  { match: /^\/card-templates(\?|$)/, ttl: FIVE_MIN },
]

const cache = new Map() // key -> { data, expireAt }

function ruleFor(url) {
  return CACHE_RULES.find((r) => r.match.test(url)) || null
}

export function isCacheable(url) {
  return ruleFor(url) !== null
}

export function getCache(url) {
  const item = cache.get(url)
  if (!item) return null
  if (Date.now() > item.expireAt) {
    cache.delete(url)
    return null
  }
  return item.data
}

export function setCache(url, data) {
  const rule = ruleFor(url)
  if (!rule) return
  cache.set(url, { data, expireAt: Date.now() + rule.ttl })
}

export function clearCache() {
  cache.clear()
}

// 调试用：返回当前缓存条目（含剩余毫秒）
export function _debugCache() {
  const out = []
  for (const [k, v] of cache.entries()) {
    out.push({ url: k, remainingMs: v.expireAt - Date.now() })
  }
  return out
}
