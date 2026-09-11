<script setup>
import { computed, onMounted, ref } from 'vue'
import { fmtNum, loadJson } from '../composables/useRemoteData'

const props = defineProps({
  limit: { type: Number, default: 10 }
})

const loading = ref(true)
const list = ref([])

onMounted(async () => {
  try {
    const idx = await loadJson('data/index.json')
    list.value = Array.isArray(idx && idx.topDps) ? idx.topDps : []
  } catch {
    /* 忽略 */
  } finally {
    loading.value = false
  }
})

const rows = computed(() => list.value.slice(0, props.limit))
const max = computed(() => {
  const m = Math.max(...rows.value.map((r) => (typeof r.dps === 'number' ? r.dps : 0)), 0)
  return m > 0 ? m : 1
})
</script>

<template>
  <div class="top-dps">
    <p v-if="loading" class="td-hint">正在加载 DPS 排行…</p>
    <p v-else-if="!rows.length" class="td-hint">暂无 DPS 数据。</p>
    <ol v-else class="td-list">
      <li v-for="(r, i) in rows" :key="r.id" class="td-row">
        <span class="td-rank">{{ i + 1 }}</span>
        <a class="td-name" :href="`/units/${r.id}`">{{ r.name || r.id }}</a>
        <span class="td-bar-wrap">
          <span class="td-bar" :style="{ width: (Math.max(r.dps || 0, 0) / max) * 100 + '%' }"></span>
        </span>
        <span class="td-dps mz-mono">{{ fmtNum(r.dps) }}</span>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.top-dps {
  margin: 1rem 0 1.5rem;
}

.td-hint {
  color: var(--vp-c-text-3);
  font-size: 0.9rem;
}

.td-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.td-row {
  display: grid;
  grid-template-columns: 1.6rem minmax(6rem, 12rem) 1fr auto;
  gap: 0.6rem;
  align-items: center;
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--mz-border);
}

.td-rank {
  font-family: var(--vp-font-family-mono);
  font-size: 0.8rem;
  color: var(--vp-c-text-3);
  text-align: right;
}

.td-name {
  color: var(--vp-c-text-1);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-decoration: none;
}

.td-name:hover {
  color: var(--mz-accent);
}

.td-bar-wrap {
  display: block;
  height: 0.5rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.td-bar {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--mz-accent), var(--mz-accent-2));
}

.td-dps {
  font-size: 0.85rem;
  color: var(--mz-accent);
  font-weight: 600;
  min-width: 4.5rem;
  text-align: right;
}

@media (max-width: 640px) {
  .td-row {
    grid-template-columns: 1.4rem 1fr auto;
  }
  .td-bar-wrap {
    display: none;
  }
}
</style>