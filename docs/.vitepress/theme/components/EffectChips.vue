<script setup>
/**
 * 「这个单位/建筑会施加哪些状态效果」的反向链接。
 *
 * 状态效果页正向列出施加者，这里补上反向边 —— 否则从劫难/天谴的页面
 * 走不到余劫那一页。effects.json 是构建期 import，不做任何请求。
 */
import { computed } from 'vue'
import effectsData from '../../../data/effects.json'
import { pageUrl } from '../composables/useRemoteData'

const props = defineProps({
  kind: { type: String, required: true }, // 'unit' | 'block'
  id: { type: String, default: '' }
})

const hits = computed(() => {
  if (!props.id) return []
  return (Array.isArray(effectsData) ? effectsData : [])
    .filter((e) =>
      (e.appliers || []).some((a) => a.kind === props.kind && a.id === props.id)
    )
    .map((e) => ({
      id: e.id,
      nameZh: e.nameZh || e.id,
      color: e.color ? '#' + String(e.color).slice(0, 6) : null,
      summary: (e.mods || [])
        .map((m) => `${m.label} ${m.percent > 0 ? '+' : ''}${m.percent}%`)
        .join(' / ')
    }))
})
</script>

<template>
  <div v-if="hits.length" class="eff-chips">
    <span class="eff-label">施加状态</span>
    <a
      v-for="h in hits"
      :key="h.id"
      class="eff-chip"
      :href="pageUrl('/effects/' + h.id)"
      :title="h.summary"
    >
      <span
        class="eff-dot"
        :style="{ background: h.color || 'var(--vp-c-text-3)' }"
      />
      <span class="eff-name">{{ h.nameZh }}</span>
      <span v-if="h.summary" class="eff-mods">{{ h.summary }}</span>
    </a>
  </div>
</template>

<style scoped>
.eff-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin: 0.75rem 0;
}
.eff-label {
  font-size: 0.78rem;
  color: var(--vp-c-text-3);
}
.eff-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.18rem 0.6rem;
  border: 1px solid var(--mz-border, rgba(255, 255, 255, 0.12));
  border-radius: 999px;
  background: var(--mz-surface, rgba(255, 255, 255, 0.04));
  text-decoration: none;
  transition: border-color 0.15s ease;
}
.eff-chip:hover {
  border-color: var(--vp-c-brand-1);
  text-decoration: none;
}
.eff-dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 2px;
  flex: none;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.18);
}
.eff-name {
  font-size: 0.82rem;
  color: var(--vp-c-text-1);
}
.eff-mods {
  font-family: var(--vp-font-family-mono);
  font-size: 0.7rem;
  color: var(--vp-c-text-3);
}
</style>
