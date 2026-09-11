<script setup>
import { computed, ref } from 'vue'
import { fmtNum, unitUrl } from '../composables/useRemoteData'
import indexData from '../../../data/index.json'

// 构建期注入，不再运行时 fetch：SSR 直接出内容，首屏不空白，
// 也不会因为静态托管上的路径问题整页空掉。
const loading = ref(false)
const error = ref('')
const all = computed(() => (Array.isArray(indexData.units) ? indexData.units : []))

const star = ref('all')
const author = ref('all')
const mode = ref('total') // total | air | ground

/**
 * 按当前口径取出一个单位的 DPS 值。
 * 必须定义在 script 里 —— 模板中的 pickOf(...) 就是调它，
 * 早期版本漏了定义，导致 /dps 页整页运行时崩溃。
 */
function pickOf(u) {
  if (!u) return 0
  if (mode.value === 'air') return u.air
  if (mode.value === 'ground') return u.ground
  if (mode.value === 'direct') return u.direct
  if (mode.value === 'splash') return u.splash
  return u.dps
}

const stars = computed(() => Array.from(new Set(all.value.map((u) => u.star).filter(Boolean))).sort())
const authors = computed(() => Array.from(new Set(all.value.map((u) => u.author).filter(Boolean))).sort())

const rows = computed(() =>
  all.value
    .filter((u) => {
      if (star.value !== 'all' && u.star !== star.value) return false
      if (author.value !== 'all' && u.author !== author.value) return false
      return true
    })
    .slice()
    .sort((a, b) => (Number(pickOf(b)) || 0) - (Number(pickOf(a)) || 0))
)

const modeLabel = computed(
  () => ({ air: '对空', ground: '对地', total: '总', direct: '单体', splash: '范围' })[mode.value] || '总'
)

const max = computed(() => {
  const m = Math.max(...rows.value.map((r) => Number(pickOf(r)) || 0), 0)
  return m > 0 ? m : 1
})
</script>

<template>
  <div class="ranking">
    <div class="rank-bar">
      <label class="rank-field">
        <span>星球</span>
        <select v-model="star">
          <option value="all">全部</option>
          <option v-for="s in stars" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
      <label class="rank-field">
        <span>作者</span>
        <select v-model="author">
          <option value="all">全部</option>
          <option v-for="a in authors" :key="a" :value="a">{{ a }}</option>
        </select>
      </label>
      <label class="rank-field">
        <span>口径</span>
        <select v-model="mode">
          <option value="total">总 DPS（单体 + 范围）</option>
          <option value="direct">单体 DPS</option>
          <option value="splash">范围 DPS</option>
          <option value="air">对空 DPS</option>
          <option value="ground">对地 DPS</option>
        </select>
      </label>
    </div>

    <p v-if="loading" class="rank-hint">正在加载…</p>
    <p v-else-if="error" class="rank-hint error">加载失败：{{ error }}</p>
    <p v-else class="rank-hint">共 {{ rows.length }} 个单位，按{{ modeLabel }} DPS 降序</p>

    <ol class="rank-list">
      <li v-for="(r, i) in rows" :key="r.id" class="rank-row">
        <span class="rank-no">{{ i + 1 }}</span>
        <a class="rank-name" :href="unitUrl(r.id)">{{ r.nameZh || r.id }}</a>
        <span class="rank-meta">
          <span :class="['mz-badge', 'star-' + (r.star || '')]">{{ r.star || '?' }}</span>
          <span v-if="r.author" class="mz-badge author">{{ r.author }}</span>
        </span>
        <span class="rank-bar-wrap">
          <span
            class="rank-bar"
            :style="{ width: (Math.max(Number(pickOf(r)) || 0, 0) / max) * 100 + '%' }"
          ></span>
        </span>
        <span class="rank-val mz-mono">{{ fmtNum(pickOf(r)) }}</span>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.rank-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  align-items: flex-end;
  margin: 1rem 0 0.6rem;
  padding: 0.8rem 0.95rem;
  border: 1px solid var(--mz-border);
  border-radius: 12px;
  background: var(--mz-surface);
}

.rank-field {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.75rem;
  color: var(--vp-c-text-3);
}

.rank-field select {
  padding: 0.38rem 0.5rem;
  border-radius: 8px;
  border: 1px solid var(--mz-border-strong);
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  font-size: 0.85rem;
}

.rank-hint {
  font-size: 0.85rem;
  color: var(--vp-c-text-3);
  margin: 0 0 0.75rem;
}

.rank-hint.error {
  color: #ff7b7b;
}

.rank-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.rank-row {
  display: grid;
  grid-template-columns: 2rem minmax(6rem, 11rem) auto 1fr auto;
  gap: 0.6rem;
  align-items: center;
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--mz-border);
}

.rank-no {
  font-family: var(--vp-font-family-mono);
  font-size: 0.8rem;
  color: var(--vp-c-text-3);
  text-align: right;
}

.rank-name {
  color: var(--vp-c-text-1);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-decoration: none;
}

.rank-name:hover {
  color: var(--mz-accent);
}

.rank-meta {
  display: flex;
  gap: 0.25rem;
}

.rank-bar-wrap {
  display: block;
  height: 0.5rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.rank-bar {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--mz-accent), var(--mz-accent-2));
}

.rank-val {
  font-size: 0.85rem;
  color: var(--mz-accent);
  font-weight: 600;
  min-width: 5rem;
  text-align: right;
}

@media (max-width: 720px) {
  .rank-row {
    grid-template-columns: 1.6rem 1fr auto;
  }
  .rank-meta,
  .rank-bar-wrap {
    display: none;
  }
}
</style>