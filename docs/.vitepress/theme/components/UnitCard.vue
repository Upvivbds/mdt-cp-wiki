<script setup>
import { computed } from 'vue'
import { fmtNum, starLabel } from '../composables/useRemoteData'

const props = defineProps({
  unit: { type: Object, required: true },
  /** 完整记录（可选）：有的话卡片显示更多信息 */
  detail: { type: Object, default: null }
})

const u = computed(() => props.unit || {})
const id = computed(() => u.value.id || '')
const link = computed(() => `/units/${id.value}`)
const nameZh = computed(() => u.value.nameZh || id.value)
const showEn = computed(() => !!u.value.nameZh && u.value.nameZh !== id.value)
const dps = computed(() => u.value.dps)
const health = computed(() => u.value.health)
</script>

<template>
  <a class="unit-card" :href="link">
    <div class="uc-head">
      <div class="uc-names">
        <span class="uc-zh">{{ nameZh }}</span>
        <span v-if="showEn" class="uc-en mz-mono">{{ id }}</span>
      </div>
      <span class="uc-tier" v-if="u.tier !== null && u.tier !== undefined">T{{ u.tier }}</span>
    </div>

    <div class="uc-badges">
      <span :class="['mz-badge', 'star-' + (u.star || '')]">{{ u.star || '?' }} · {{ starLabel(u.star) }}</span>
      <span v-if="u.author" class="mz-badge author">{{ u.author }}</span>
      <span v-if="u.category" class="mz-badge">{{ u.category }}</span>
    </div>

    <div class="uc-stats">
      <div class="uc-stat">
        <span class="uc-stat-label">DPS</span>
        <span class="uc-stat-value accent">{{ fmtNum(dps) }}</span>
      </div>
      <div class="uc-stat">
        <span class="uc-stat-label">对空</span>
        <span class="uc-stat-value">{{ fmtNum(u.air) }}</span>
      </div>
      <div class="uc-stat">
        <span class="uc-stat-label">血量</span>
        <span class="uc-stat-value">{{ fmtNum(health, 0) }}</span>
      </div>
    </div>
  </a>
</template>

<style scoped>
.unit-card {
  display: block;
  padding: 0.85rem 0.95rem;
  border-radius: 12px;
  border: 1px solid var(--mz-border);
  background: linear-gradient(155deg, var(--mz-surface-2), var(--mz-surface));
  text-decoration: none !important;
  color: inherit;
  transition: transform 0.14s ease, border-color 0.14s ease, box-shadow 0.14s ease;
}

.unit-card:hover {
  transform: translateY(-2px);
  border-color: var(--mz-border-strong);
  box-shadow: var(--mz-glow);
}

.uc-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
}

.uc-names {
  display: flex;
  align-items: baseline;
  gap: 0.45rem;
  min-width: 0;
}

.uc-zh {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--vp-c-text-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.uc-en {
  font-size: 0.76rem;
  color: var(--vp-c-text-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.uc-tier {
  flex: none;
  font-family: var(--vp-font-family-mono);
  font-size: 0.75rem;
  color: var(--mz-accent-2);
  border: 1px solid color-mix(in srgb, var(--mz-accent-2) 40%, transparent);
  border-radius: 6px;
  padding: 0 0.3rem;
}

.uc-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin: 0.55rem 0 0.65rem;
}

.uc-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.4rem;
  padding-top: 0.55rem;
  border-top: 1px solid var(--mz-border);
}

.uc-stat {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.uc-stat-label {
  font-size: 0.7rem;
  color: var(--vp-c-text-3);
}

.uc-stat-value {
  font-family: var(--vp-font-family-mono);
  font-size: 0.9rem;
  color: var(--vp-c-text-1);
  overflow: hidden;
  text-overflow: ellipsis;
}

.uc-stat-value.accent {
  color: var(--mz-accent);
  font-weight: 700;
}
</style>