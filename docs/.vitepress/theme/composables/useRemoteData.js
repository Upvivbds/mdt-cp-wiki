/**
 * 完整数据（units.json / buildings.json）体积较大，放在 docs/public/data/ 下，
 * 构建时整体复制到 dist 根目录，运行时通过 HTTP 按需获取。
 * 这里做一层模块级缓存：同一次页面会话内只请求一次。
 */

const cache = new Map()

function resolveUrl(path) {
  const base =
    (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.BASE_URL) || '/'
  const b = base.endsWith('/') ? base : base + '/'
  return b + String(path).replace(/^\/+/, '')
}

export function loadJson(path) {
  if (!cache.has(path)) {
    const p = fetch(resolveUrl(path), { credentials: 'same-origin' })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status} — 无法加载 ${path}`)
        return res.json()
      })
      .catch((err) => {
        cache.delete(path)
        throw err
      })
    cache.set(path, p)
  }
  return cache.get(path)
}

/** @returns {Promise<Array>} 全部单位完整记录 */
export function loadUnits() {
  return loadJson('data/units.json').then((d) => (Array.isArray(d) ? d : []))
}

/** @returns {Promise<Array>} 全部建筑完整记录 */
export function loadBuildings() {
  return loadJson('data/buildings.json').then((d) => (Array.isArray(d) ? d : []))
}

/* ---------- 通用小工具（组件之间共用，字段一律容错） ---------- */

export function isNum(v) {
  return typeof v === 'number' && Number.isFinite(v)
}

/** 把可能是数字、字符串、null 的值统一成数字或 null */
export function toNum(v) {
  if (isNum(v)) return v
  if (typeof v === 'string') {
    const s = v.trim()
    if (s && Number.isFinite(Number(s))) return Number(s)
  }
  return null
}

export function fmtNum(v, digits = 2) {
  const n = toNum(v)
  if (n === null) return '—'
  const f = Math.pow(10, digits)
  const r = Math.round(n * f) / f
  return String(r)
}

export function fmtAny(v) {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'boolean') return v ? '是' : '否'
  if (typeof v === 'number') return isNum(v) ? String(Math.round(v * 1000) / 1000) : '—'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

export function starLabel(star) {
  if (star === 'S') return '赛普罗'
  if (star === 'E') return '埃里克尔'
  return star || '未知'
}

/* ---------- 站内链接 ----------
 * VitePress 只对 Markdown 里写的链接自动补 `.html`，组件里手写的
 * `:href="`/units/${id}`"` 不会 —— 静态托管上会 404（文件其实是
 * units/<id>.html）。所以站内链接一律走这里生成。
 *
 * 与 config.mts 的 `cleanUrls: false` 保持一致：改配置时这里要同步。
 */
export function pageUrl(path) {
  let p = String(path == null ? '' : path).trim()
  if (!p) return '/'
  if (/^(https?:)?\/\//.test(p) || p.startsWith('#') || p.startsWith('mailto:')) return p
  if (!p.startsWith('/')) p = '/' + p
  if (p.endsWith('/')) return p
  if (/\.html?$/.test(p)) return p
  return p + '.html'
}

/** 单位详情页 URL */
export function unitUrl(id) {
  return pageUrl('units/' + id)
}

/** 建筑详情页 URL */
export function buildingUrl(id) {
  return pageUrl('buildings/' + id)
}
