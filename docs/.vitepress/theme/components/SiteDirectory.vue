<script setup>
/**
 * 首页的全站目录。
 *
 * 早期首页只放统计数字和 DPS 榜，但 wiki 的实际使用方式是「找到某个页面点进去」，
 * 所以这里把所有可用页面按版块列全：单位按星球/分类、建筑按类型、外加其余页面。
 * 数据来自 index.json（构建期 import，无网络请求）。
 */
import { computed } from 'vue'
import { unitUrl, buildingUrl, pageUrl } from '../composables/useRemoteData'

import indexData from '../../../data/index.json'
import effectsData from '../../../data/effects.json'

const units = computed(() => (Array.isArray(indexData.units) ? indexData.units : []))
const blocks = computed(() => (Array.isArray(indexData.blocks) ? indexData.blocks : []))
const effects = computed(() => (Array.isArray(effectsData) ? effectsData : []))

/** 单位：星球 → 分类 → [单位] */
const unitSections = computed(() => {
  const buckets = { 赛普罗: {}, 埃里克尔: {}, 其他: {} }
  for (const u of units.value) {
    const cat = u.category || '未分类'
    const star = cat.includes('赛普罗') ? '赛普罗' : cat.includes('埃里克尔') ? '埃里克尔' : '其他'
    ;(buckets[star][cat] ||= []).push(u)
  }
  return Object.entries(buckets)
    .map(([star, cats]) => ({
      star,
      total: Object.values(cats).reduce((n, a) => n + a.length, 0),
      groups: Object.entries(cats).map(([cat, list]) => ({
        cat,
        list: list.slice().sort((a, b) => (a.tier || 99) - (b.tier || 99) || (a.nameZh || '').localeCompare(b.nameZh || ''))
      }))
    }))
    .filter((s) => s.total > 0)
    .sort((a, b) => b.total - a.total)
})

/** 建筑：类型 → [建筑] */
const blockSections = computed(() => {
  const cats = {}
  for (const b of blocks.value) {
    ;(cats[b.category || '其他'] ||= []).push(b)
  }
  return Object.entries(cats).map(([cat, list]) => ({
    cat,
    list: list.slice().sort((a, b) => (a.nameZh || '').localeCompare(b.nameZh || ''))
  }))
})

const otherPages = [
  { link: '/dps', title: 'DPS 排行', desc: '单体 / 范围 / 对空 / 对地四种口径' },
  { link: '/units/', title: '单位总览', desc: '卡片网格，可按星球、作者、分类筛选' },
  { link: '/buildings/', title: '建筑总览', desc: '炮塔弹药与墙体改动' },
  { link: '/effects/', title: '状态效果', desc: '数据包新增的 status.* 与施加者' },
  { link: '/about', title: '关于本站', desc: '数据来源与 DPS 公式说明' }
]

/** 状态效果条目少，直接把修正项摊开写，省得再点一层。 */
function effectSummary(e) {
  const mods = e.mods || []
  if (!mods.length) return '无数值修正'
  return mods.map((m) => `${m.label} ${m.percent > 0 ? '+' : ''}${m.percent}%`).join(' · ')
}
</script>

<template>
  <div class="dir">
    <!-- 其余页面 -->
    <section class="dir-block">
      <h2 class="dir-title">站点导航</h2>
      <div class="dir-cards">
        <a v-for="p in otherPages" :key="p.link" class="dir-card" :href="pageUrl(p.link)">
          <span class="dir-card-title">{{ p.title }}</span>
          <span class="dir-card-desc">{{ p.desc }}</span>
        </a>
      </div>
    </section>

    <!-- 单位 -->
    <section v-for="s in unitSections" :key="s.star" class="dir-block">
      <h2 class="dir-title">
        单位 · {{ s.star }}
        <span class="dir-count">{{ s.total }}</span>
      </h2>
      <div v-for="g in s.groups" :key="g.cat" class="dir-group">
        <h3 class="dir-sub">{{ g.cat }}<span class="dir-count">{{ g.list.length }}</span></h3>
        <ul class="dir-list">
          <li v-for="u in g.list" :key="u.id">
            <a :href="unitUrl(u.id)">{{ u.nameZh || u.id }}</a>
            <span v-if="u.tier" class="dir-tier">T{{ u.tier }}</span>
            <span class="dir-dps">{{ Math.round(u.dps || 0) }}</span>
          </li>
        </ul>
      </div>
    </section>

    <!-- 状态效果 -->
    <section v-if="effects.length" class="dir-block">
      <h2 class="dir-title">
        状态效果
        <span class="dir-count">{{ effects.length }}</span>
      </h2>
      <ul class="dir-list">
        <li v-for="e in effects" :key="e.id">
          <span
            class="dir-swatch"
            :style="{ background: e.color ? '#' + String(e.color).slice(0, 6) : 'var(--vp-c-text-3)' }"
          />
          <a :href="pageUrl('/effects/' + e.id)">{{ e.nameZh || e.id }}</a>
          <span class="dir-note">{{ effectSummary(e) }}</span>
        </li>
      </ul>
    </section>

    <!-- 建筑 -->
    <section class="dir-block">
      <h2 class="dir-title">
        建筑
        <span class="dir-count">{{ blocks.length }}</span>
      </h2>
      <div v-for="g in blockSections" :key="g.cat" class="dir-group">
        <h3 class="dir-sub">{{ g.cat }}<span class="dir-count">{{ g.list.length }}</span></h3>
        <ul class="dir-list">
          <li v-for="b in g.list" :key="b.id">
            <a :href="buildingUrl(b.id)">{{ b.nameZh || b.id }}</a>
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>

<style scoped>
.dir {
  margin-top: 1.6rem;
}

.dir-block {
  margin-bottom: 2rem;
}

.dir-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.9rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--mz-border);
  font-size: 1.15rem;
  border-top: none;
}

.dir-count {
  padding: 0.05rem 0.5rem;
  border-radius: 999px;
  border: 1px solid var(--mz-border-strong);
  background: var(--mz-surface);
  font-family: var(--vp-font-family-mono);
  font-size: 0.72rem;
  font-weight: 400;
  color: var(--vp-c-text-3);
}

.dir-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 0.75rem;
}

.dir-card {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.85rem 1rem;
  border: 1px solid var(--mz-border);
  border-radius: 10px;
  background: var(--mz-surface);
  text-decoration: none !important;
  transition: border-color 0.16s ease, transform 0.16s ease;
}

.dir-card:hover {
  border-color: var(--mz-border-strong);
  transform: translateY(-2px);
}

.dir-card-title {
  font-weight: 650;
  color: var(--mz-accent);
}

.dir-card-desc {
  font-size: 0.78rem;
  color: var(--vp-c-text-3);
}

.dir-group {
  margin-bottom: 1rem;
}

.dir-sub {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0 0 0.45rem;
  padding: 0;
  border: none;
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--mz-accent-2);
}

.dir-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.2rem 0.8rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.dir-list li {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
  padding: 0.18rem 0.35rem;
  border-radius: 6px;
  font-size: 0.86rem;
}

.dir-list li:hover {
  background: var(--mz-surface);
}

.dir-list a {
  color: var(--vp-c-text-1) !important;
  text-decoration: none !important;
}

.dir-list a:hover {
  color: var(--mz-accent) !important;
}

.dir-tier {
  padding: 0 0.3rem;
  border-radius: 4px;
  background: rgba(255, 165, 61, 0.14);
  font-size: 0.68rem;
  color: var(--mz-accent-2);
}

.dir-dps {
  margin-left: auto;
  font-family: var(--vp-font-family-mono);
  font-size: 0.72rem;
  color: var(--vp-c-text-3);
}
.dir-swatch {
  flex: none;
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 2px;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.18);
}
.dir-note {
  margin-left: auto;
  font-family: var(--vp-font-family-mono);
  font-size: 0.7rem;
  color: var(--vp-c-text-3);
  text-align: right;
}
</style>
