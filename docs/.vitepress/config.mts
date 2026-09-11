import { defineConfig } from 'vitepress'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DOCS = path.resolve(__dirname, '..')

/**
 * 紧凑索引（约 20KB）在构建期读取，用于生成导航与侧边栏。
 * 生成脚本可能把它写在 docs/data/index.json（优先），
 * 也可能只留在 docs/public/data/index.json —— 两处都试，读不到就退化成空索引，
 * 保证站点在任何情况下都能构建通过。
 */
function loadIndex(): any {
  const candidates = [
    path.join(DOCS, 'data', 'index.json'),
    path.join(DOCS, 'public', 'data', 'index.json')
  ]
  for (const p of candidates) {
    try {
      if (fs.existsSync(p)) return JSON.parse(fs.readFileSync(p, 'utf8'))
    } catch {
      /* 忽略，继续尝试下一个候选路径 */
    }
  }
  return {}
}

const indexData = loadIndex()

interface UnitIndexRow {
  id: string
  nameZh?: string | null
  star?: string | null
  author?: string | null
  category?: string | null
  tier?: number | null
  dps?: number | null
  air?: number | null
  health?: number | null
}

const units: UnitIndexRow[] = Array.isArray(indexData.units) ? indexData.units : []
const categories: Record<string, string[]> = indexData.categories || {}

const unitById: Record<string, UnitIndexRow> = {}
for (const u of units) {
  if (u && u.id) unitById[u.id] = u
}

function unitLabel(id: string): string {
  const u = unitById[id]
  const zh = u && u.nameZh && u.nameZh !== id ? u.nameZh : ''
  return zh ? `${zh}（${id}）` : id
}

const unitGroups = Object.keys(categories).map((cat) => ({
  text: cat,
  collapsed: true,
  items: (categories[cat] || []).map((id) => ({
    text: unitLabel(id),
    link: `/units/${id}`
  }))
}))

const unitSidebar = [
  {
    text: '单位',
    items: [{ text: '全部单位', link: '/units/' }]
  },
  {
    text: '按分类浏览',
    collapsed: false,
    items: Object.keys(categories).map((c) => ({ text: c, link: '/units/' }))
  },
  ...unitGroups
]

const buildingSidebar = [
  {
    text: '建筑',
    items: [
      { text: '全部建筑', link: '/buildings/' },
      { text: 'DPS 排行', link: '/dps' }
    ]
  }
]

const rootSidebar = [
  {
    text: '总览',
    items: [
      { text: '首页', link: '/' },
      { text: '单位总览', link: '/units/' },
      { text: '建筑总览', link: '/buildings/' },
      { text: 'DPS 排行', link: '/dps' },
      { text: '关于', link: '/about' }
    ]
  }
]

export default defineConfig({
  lang: 'zh-CN',
  title: 'Mindustry 数据包 Wiki',
  description:
    'Mindustry 数据包单位与建筑图鉴：中文名、原版数值对比、DPS 计算与能力一览。',
  appearance: 'dark',
  cleanUrls: false,
  head: [
    ['meta', { name: 'theme-color', content: '#0b0f14' }],
    ['meta', { name: 'color-scheme', content: 'dark' }]
  ],
  themeConfig: {
    siteTitle: 'Mindustry 数据包 Wiki',
    nav: [
      { text: '首页', link: '/' },
      { text: '单位', link: '/units/' },
      { text: '建筑', link: '/buildings/' },
      { text: 'DPS 排行', link: '/dps' },
      { text: '关于', link: '/about' }
    ],
    sidebar: {
      '/units/': unitSidebar,
      '/buildings/': buildingSidebar,
      '/': rootSidebar
    },
    search: {
      provider: 'local',
      options: {
        translations: {
          button: {
            buttonText: '搜索文档',
            buttonAriaLabel: '搜索文档'
          },
          modal: {
            noResultsText: '无法找到相关结果',
            resetButtonTitle: '清除查询条件',
            footer: {
              selectText: '选择',
              navigateText: '切换',
              closeText: '关闭'
            }
          }
        }
      }
    },
    outline: {
      level: [2, 3],
      label: '本页目录'
    },
    docFooter: {
      prev: '上一篇',
      next: '下一篇'
    },
    darkModeSwitchLabel: '外观',
    lightModeSwitchTitle: '切换到浅色模式',
    darkModeSwitchTitle: '切换到深色模式',
    sidebarMenuLabel: '目录',
    returnToTopLabel: '回到顶部',
    externalLinkIcon: true,
    footer: {
      message: '数据由数据包 hjson 自动解析生成，仅供参考',
      copyright: 'Mindustry 数据包 Wiki'
    }
  }
})