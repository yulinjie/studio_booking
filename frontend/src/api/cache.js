/*
  请求级内存缓存：稳定的 GET 接口（课程类型 / 课程列表 / 教练 / 工作室配置等）
  按 URL 配置不同 TTL，避免一刀切。

  使用：client.js 在 GET 拦截里 `getCache(url)`，命中直接 resolve；
  写操作（POST/PATCH/DELETE）后调 `invalidate(prefix)` 清相关 key。
*/

// 不同接口的 TTL 配置（毫秒）
const ONE_MIN = 60 * 1000
const FIVE_MIN = 5 * 60 * 1000
const HALF_HOUR = 30 * 60 * 1000
const ONE_HOUR = 60 * 60 * 1000

const CACHE_RULES = [
  // 工作室配置：基本不变，缓存 1 小时
  { match: /^\/studio\/config$/, ttl: ONE_HOUR },

  // 课程 / 教练 / 类目：变动不频繁，半小时
  { match: /^\/courses(\?|$)/, ttl: HALF_HOUR },
  { match: /^\/admin\/courses(\?|$)/, ttl: HALF_HOUR },
  { match: /^\/coaches(\?|$)/, ttl: HALF_HOUR },
  { match: /^\/coaches\/\d+\/profile$/, ttl: HALF_HOUR },
  { match: /^\/course-categories(\?|$)/, ttl: HALF_HOUR },
  { match: /^\/admin\/course-categories(\?|$)/, ttl: HALF_HOUR },

  // 卡模板：偶尔调价，5 分钟
  { match: /^\/card-templates(\?|$)/, ttl: FIVE_MIN },
  { match: /^\/admin\/card-templates(\?|$)/, ttl: FIVE_MIN },
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

// prefix 是路径前缀，命中即清。例如 invalidate('/courses') 会清掉
// 所有 /courses 和 /courses?xxx 缓存
export function invalidate(prefix) {
  for (const k of cache.keys()) {
    if (k.startsWith(prefix)) cache.delete(k)
  }
}

export function clearCache() {
  cache.clear()
}

// 调试用：返回当前缓存条目（含到期时间）
export function _debugCache() {
  const out = []
  for (const [k, v] of cache.entries()) {
    out.push({ url: k, remainingMs: v.expireAt - Date.now() })
  }
  return out
}
