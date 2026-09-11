<script setup>
import { computed, ref } from 'vue'
import UnitCard from './UnitCard.vue'
import indexData from '../../../data/index.json'

const props = defineProps({
  /** 可选的初始筛选（例如 /units/#分类 锚点用不到，这里保留给将来扩展） */
  initialCategory: { type: String, default: '' }
})

// 构建期注入：SSR 直接出完整卡片网格（含贴图），首屏不空白。
const loading = ref(false)
const error = ref('')
const all = computed(() => (Array.isArray(indexData.units) ? indexData.units : []))

const star = ref('all')
const author = ref('all')
const category = ref(props.initialCategory || 'all')
const sortKey = ref('dps-desc')
const keyword = ref('')

const stars = computed(() => {
  const s = new Set(all.value.map((u) => u.star).filter(Boolean))
  return Array.from(s).sort()
})

const authors = computed(() => {
  const s = new Set(all.value.map((u) => u.author).filter(Boolean))
  return Array.from(s).sort()
})

const categories = computed(() => {
  const s = new Set(all.value.map((u) => u.category).filter(Boolean))
  return Array.from(s).sort()
})

const SORTS = [
  { key: 'dps-desc', label: 'DPS 从高到低' },
  { key: 'dps-asc', label: 'DPS 从低到高' },
  { key: 'health-desc', label: '血量从高到低' },
  { key: 'health-asc', label: '血量从低到高' },
  { key: 'tier-desc', label: 'T 级从高到低' },
  { key: 'tier-asc', label: 'T 级从低到高' },
  { key: 'name', label: '名称' }
]

const num = (v, fallback = -Infinity) => (typeof v === 'number' && Number.isFinite(v) ? v : fallback)

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  let list = all.value.filter((u) => {
    if (!u) return false
    if (star.value !== 'all' && u.star !== star.value) return false
    if (author.value !== 'all' && u.author !== author.value) return false
    if (category.value !== 'all' && u.category !== category.value) return false
    if (kw) {
      const hay = `${u.nameZh || ''} ${u.id || ''}`.toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })

  const [key, dir] = sortKey.value.split('-')
  const asc = dir === 'asc'
  list = list.slice().sort((a, b) => {
    let r
    if (key === 'dps') r = num(a.dps, -1) - num(b.dps, -1)
    else if (key === 'health') r = num(a.health, -1) - num(b.health, -1)
    else if (key === 'tier') r = num(a.tier, -1) - num(b.tier, -1)
    else r = String(a.nameZh || a.id || '').localeCompare(String(b.nameZh || b.id || ''), 'zh')
    return asc ? r : -r
  })
  return list
})

function reset() {
  star.value = 'all'
  author.value = 'all'
  category.value = 'all'
  sortKey.value = 'dps-desc'
  keyword.value = ''
}

const isDirty = computed(
  () =>
    star.value !== 'all' ||
    author.value !== 'all' ||
    category.value !== 'all' ||
    keyword.value !== '' ||
    sortKey.value !== 'dps-desc'
)
</script>

<template>
  <div class="browser">
    <div class="browser-bar">
      <input v-model="keyword" class="browser-search" type="search" placeholder="搜索中文名或英文 id…" />

      <label class="browser-field">
        <span>星球</span>
        <select v-model="star">
          <option value="all">全部</option>
          <option v-for="s in stars" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>

      <label class="browser-field">
        <span>作者</span>
        <select v-model="author">
          <option value="all">全部</option>
          <option v-for="a in authors" :key="a" :value="a">{{ a }}</option>
        </select>
      </label>

      <label class="browser-field">
        <span>分类</span>
        <select v-model="category">
          <option value="all">全部</option>
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </select>
      </label>

      <label class="browser-field">
        <span>排序</span>
        <select v-model="sortKey">
          <option v-for="s in SORTS" :key="s.key" :value="s.key">{{ s.label }}</option>
        </select>
      </label>

      <button type="button" class="browser-reset" :disabled="!isDirty" @click="reset">重置</button>
    </div>

    <p v-if="loading" class="browser-hint">正在加载单位索引…</p>
    <p v-else-if="error" class="browser-hint error">加载失败：{{ error }}</p>
    <p v-else class="browser-hint">
      共 <strong>{{ filtered.length }}</strong> / {{ all.length }} 个单位
    </p>

    <div class="browser-grid">
      <UnitCard v-for="u in filtered" :key="u.id" :unit="u" />
    </div>

    <p v-if="!loading && !error && !filtered.length" class="browser-hint">
      没有符合当前筛选条件的单位 (´･ω･`)
    </p>
  </div>
</template>

<style scoped>
.browser-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: flex-end;
  margin: 1rem 0 0.75rem;
  padding: 0.85rem 0.95rem;
  border: 1px solid var(--mz-border);
  border-radius: 12px;
  background: var(--mz-surface);
}

.browser-search {
  flex: 1 1 14rem;
  min-width: 12rem;
  padding: 0.4rem 0.6rem;
  border-radius: 8px;
  border: 1px solid var(--mz-border-strong);
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  font-size: 0.9rem;
}

.browser-field {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.75rem;
  color: var(--vp-c-text-3);
}

.browser-field select {
  padding: 0.38rem 0.5rem;
  border-radius: 8px;
  border: 1px solid var(--mz-border-strong);
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  font-size: 0.85rem;
}

.browser-reset {
  padding: 0.42rem 0.9rem;
  border-radius: 8px;
  border: 1px solid var(--mz-border-strong);
  background: transparent;
  color: var(--vp-c-text-2);
  font-size: 0.85rem;
  cursor: pointer;
}

.browser-reset:disabled {
  opacity: 0.4;
  cursor: default;
}

.browser-hint {
  font-size: 0.85rem;
  color: var(--vp-c-text-3);
  margin: 0.25rem 0 0.85rem;
}

.browser-hint strong {
  color: var(--mz-accent);
}

.browser-hint.error {
  color: #ff7b7b;
}

.browser-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr));
  gap: 0.75rem;
}
</style>