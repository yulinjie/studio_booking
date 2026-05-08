/*
  动态 src / href 的协议白名单校验。

  后端字段（studio.logo / studio.payment_qr / coach.avatar / course.cover / order.payment_proof
  等）都可能被注入 javascript: / data:text/html 等危险协议。统一过这里。

  允许：相对路径（/uploads/xxx）、http、https、data:image/*、blob:（本地预览）。
*/

const SAFE_PROTOCOLS = ['http:', 'https:', 'blob:']
const SAFE_DATA_PREFIX = 'data:image/'

export function isSafeUrl(value) {
  if (!value || typeof value !== 'string') return false
  const v = value.trim()
  if (!v) return false
  // 相对路径 / 站内绝对路径
  if (v.startsWith('/') && !v.startsWith('//')) return true
  // data:image/...
  if (v.toLowerCase().startsWith(SAFE_DATA_PREFIX)) return true
  try {
    const u = new URL(v, window.location.origin)
    return SAFE_PROTOCOLS.includes(u.protocol)
  } catch {
    return false
  }
}

export function safeSrc(value) {
  return isSafeUrl(value) ? value : ''
}
