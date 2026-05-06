/*
  课程类别 → 莫兰迪色卡。
  按 category.code 映射，未知类型回退到默认 sage。
*/

export const CATEGORY_PALETTE = {
  group:   { from: '#B5C4A7', to: '#7A9181', deep: '#5C7050', soft: '#DDE5DC', label: '团课' },
  private: { from: '#C8A48C', to: '#A4836B', deep: '#7A6552', soft: '#FAEEDE', label: '私教' },
  duet:    { from: '#C8A8A8', to: '#9C7676', deep: '#7A5A5A', soft: '#EDE0E1', label: '双人' },
  semi:    { from: '#B7A8B8', to: '#8A7593', deep: '#6B5876', soft: '#E2D8E4', label: '小班' },
  default: { from: '#A8B0B5', to: '#7A8186', deep: '#5C6266', soft: '#E0E3E5', label: '其他' },
}

export function colorFor(code) {
  return CATEGORY_PALETTE[code] || CATEGORY_PALETTE.default
}

export function gradient(code, dir = '135deg') {
  const c = colorFor(code)
  return `linear-gradient(${dir}, ${c.from} 0%, ${c.to} 100%)`
}

/* 给 ECharts 用的（4 段渐变 stops） */
export function echartsGradient(code) {
  const c = colorFor(code)
  return {
    type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
    colorStops: [{ offset: 0, color: c.from }, { offset: 1, color: c.to }],
  }
}
