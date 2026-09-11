<script setup>
import { computed, onMounted, ref } from 'vue'
import { loadJson } from '../composables/useRemoteData'

const loading = ref(true)
const stats = ref({ unitCount: null, blockCount: null, vanillaCount: null })

onMounted(async () => {
  try {
    const idx = await loadJson('data/index.json')
    stats.value = {
      unitCount: idx && idx.unitCount != null ? idx.unitCount : null,
      blockCount: idx && idx.blockCount != null ? idx.blockCount : null,
      vanillaCount: idx && idx.vanillaCount != null ? idx.vanillaCount : null
    }
  } catch {
    /* 首页统计卡片失败不阻塞渲染 */
  } finally {
    loading.value = false
  }
})

const cards = computed(() => [
  { label: '数据包单位', value: stats.value.unitCount, hint: '个独立单位页面' },
  { label: '数据包建筑', value: stats.value.blockCount, hint: '个建筑条目' },
  { label: '涉及原版单位', value: stats.value.vanillaCount, hint: '个可对比的原版单位' }
])
</script>

<template>
  <div class="stats-cards">
    <div v-for="c in cards" :key="c.label" class="stat-card">
      <div class="stat-value">{{ loading || c.value == null ? '—' : c.value }}</div>
      <div class="stat-label">{{ c.label }}</div>
      <div class="stat-hint">{{ c.hint }}</div>
    </div>
  </div>
</template>

<style scoped>
.stats-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.9rem;
  margin: 1.5rem 0;
}

.stat-card {
  padding: 1.1rem 1.2rem;
  border: 1px solid var(--mz-border);
  border-radius: 14px;
  background: linear-gradient(160deg, color-mix(in srgb, var(--mz-accent) 8%, var(--mz-surface)), var(--mz-surface));
  text-align: center;
}

.stat-value {
  font-family: var(--vp-font-family-mono);
  font-size: 2.1rem;
  font-weight: 700;
  color: var(--mz-accent);
  line-height: 1.15;
}

.stat-label {
  margin-top: 0.25rem;
  font-size: 0.95rem;
  color: var(--vp-c-text-1);
}

.stat-hint {
  font-size: 0.75rem;
  color: var(--vp-c-text-3);
  margin-top: 0.15rem;
}

@media (max-width: 640px) {
  .stats-cards {
    grid-template-columns: 1fr;
  }
}
</style>