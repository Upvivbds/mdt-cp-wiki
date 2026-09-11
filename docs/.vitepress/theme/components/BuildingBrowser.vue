<script setup>
import { computed, onMounted, ref } from 'vue'
import BuildingCard from './BuildingCard.vue'
import { loadJson } from '../composables/useRemoteData'

const loading = ref(true)
const error = ref('')
const all = ref([])

const star = ref('all')
const author = ref('all')
const category = ref('all')
const keyword = ref('')

onMounted(async () => {
  try {
    // 建筑完整数据（含 raw）在 public 下；这里只取列表所需字段，顺带补上 packs
    const data = await loadJson('data/buildings.json')
    all.value = Array.isArray(data) ? data : []
  } catch (e) {
    // 回退：至少用索引里的 blocks 列表
    try {
      const idx = await loadJson('data/index.json')
      all.value = Array.isArray(idx && idx.blocks) ? idx.blocks : []
    } catch (e2) {
      error.value = e && e.message ? e.message : String(e)
    }
  } finally {
    loading.value = false
  }
})

const stars = computed(() => Array.from(new Set(all.value.map((b) => b.star).filter(Boolean))).sort())
const authors = computed(() => Array.from(new Set(all.value.map((b) => b.author).filter(Boolean))).sort())
const categories = computed(() =>
  Array.from(new Set(all.value.map((b) => b.category).filter(Boolean))).sort()
)

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return all.value
    .filter((b) => {
      if (!b) return false
      if (star.value !== 'all' && b.star !== star.value) return false
      if (author.value !== 'all' && b.author !== author.value) return false
      if (category.value !== 'all' && b.category !== category.value) return false
      if (kw) {
        const hay = `${b.nameZh || ''} ${b.id || ''}`.toLowerCase()
        if (!hay.includes(kw)) return false
      }
      return true
    })
    .sort((a, b) =>
      String(a.nameZh || a.id || '').localeCompare(String(b.nameZh || b.id || ''), 'zh')
    )
})

function reset() {
  star.value = 'all'
  author.value = 'all'
  category.value = 'all'
  keyword.value = ''
}

const isDirty = computed(
  () => star.value !== 'all' || author.value !== 'all' || category.value !== 'all' || keyword.value !== ''
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

      <button type="button" class="browser-reset" :disabled="!isDirty" @click="reset">重置</button>
    </div>

    <p v-if="loading" class="browser-hint">正在加载建筑数据…</p>
    <p v-else-if="error" class="browser-hint error">加载失败：{{ error }}</p>
    <p v-else class="browser-hint">
      共 <strong>{{ filtered.length }}</strong> / {{ all.length }} 个建筑
    </p>

    <div class="browser-grid">
      <BuildingCard v-for="b in filtered" :key="b.id" :building="b" />
    </div>

    <p v-if="!loading && !error && !filtered.length" class="browser-hint">
      没有符合当前筛选条件的建筑 (´･ω･`)
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