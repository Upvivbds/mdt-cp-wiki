<script setup>
import { computed } from 'vue'
import { toNum, fmtAny } from '../composables/useRemoteData'

const props = defineProps({
  label: { type: String, default: '' },
  value: { type: [Number, String, Boolean, null], default: null },
  vanilla: { type: [Number, String, Boolean, null], default: null },
  /** 单位后缀，例如 "HP" / "tick" / "%" */
  unit: { type: String, default: '' },
  /** true = 数值越高越好；false = 数值越低越好（例如装填时间） */
  higherIsBetter: { type: Boolean, default: true },
  /** true = 不做优劣判断，只显示差值（例如 hitSize 这类中性属性） */
  neutral: { type: Boolean, default: false },
  digits: { type: Number, default: 2 }
})

function fmt(v) {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) return '—'
    const f = Math.pow(10, props.digits)
    return String(Math.round(v * f) / f)
  }
  return fmtAny(v)
}

const nv = computed(() => toNum(props.value))
const ov = computed(() => toNum(props.vanilla))

const hasBoth = computed(() => nv.value !== null && ov.value !== null)
const changed = computed(() => hasBoth.value && nv.value !== ov.value)

/** -1 = 变差, 0 = 无变化/不可比, 1 = 变好 */
const verdict = computed(() => {
  if (!changed.value) return 0
  if (props.neutral) return 0
  const up = nv.value > ov.value
  const good = props.higherIsBetter ? up : !up
  return good ? 1 : -1
})

const cls = computed(() => {
  if (!changed.value) return 'sc-row'
  if (verdict.value === 0) return 'sc-row sc-diff'
  return verdict.value > 0 ? 'sc-row sc-better' : 'sc-row sc-worse'
})

const deltaAbs = computed(() => {
  if (!hasBoth.value) return null
  return Math.round((nv.value - ov.value) * 1000) / 1000
})

const deltaPct = computed(() => {
  if (!hasBoth.value || ov.value === 0) return null
  return Math.round(((nv.value - ov.value) / Math.abs(ov.value)) * 1000) / 10
})

const deltaText = computed(() => {
  if (!hasBoth.value) return '—'
  if (!changed.value) return '±0'
  const a = deltaAbs.value
  const p = deltaPct.value
  const sign = a > 0 ? '+' : ''
  const abs = `${sign}${a}`
  if (p === null) return abs
  return `${abs}（${p > 0 ? '+' : ''}${p}%）`
})
</script>

<template>
  <div :class="cls">
    <div class="sc-label">
      {{ label }}<span v-if="unit" class="sc-unit">（{{ unit }}）</span>
    </div>
    <div class="sc-value">{{ fmt(value) }}</div>
    <div class="sc-vanilla">{{ fmt(vanilla) }}</div>
    <div class="sc-delta">
      <span v-if="!hasBoth" class="sc-muted">—</span>
      <template v-else>
        <span v-if="changed" class="sc-badge">{{ deltaText }}</span>
        <span v-else class="sc-muted">无变化</span>
      </template>
    </div>
  </div>
</template>

<style scoped>
.sc-row {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr 1.4fr;
  gap: 0.5rem;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--mz-border);
  background: var(--mz-surface);
  font-size: 0.9rem;
}

.sc-row + .sc-row {
  margin-top: 0.35rem;
}

.sc-label {
  color: var(--vp-c-text-1);
  font-weight: 500;
}

.sc-unit {
  color: var(--vp-c-text-3);
  font-size: 0.8em;
}

.sc-value {
  font-family: var(--vp-font-family-mono);
  color: var(--vp-c-text-1);
  font-weight: 600;
}

.sc-vanilla {
  font-family: var(--vp-font-family-mono);
  color: var(--vp-c-text-3);
}

.sc-delta {
  text-align: right;
  font-family: var(--vp-font-family-mono);
  font-size: 0.85rem;
}

.sc-muted {
  color: var(--vp-c-text-3);
}

.sc-badge {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  border: 1px solid currentColor;
}

.sc-better {
  border-color: color-mix(in srgb, #3ddc97 45%, transparent);
  background: color-mix(in srgb, #3ddc97 10%, var(--mz-surface));
}

.sc-better .sc-delta {
  color: #3ddc97;
}

.sc-worse {
  border-color: color-mix(in srgb, #ff6b6b 45%, transparent);
  background: color-mix(in srgb, #ff6b6b 10%, var(--mz-surface));
}

.sc-worse .sc-delta {
  color: #ff7b7b;
}

.sc-diff .sc-delta {
  color: var(--mz-accent);
}

.sc-diff {
  border-color: color-mix(in srgb, var(--mz-accent) 35%, transparent);
}

@media (max-width: 640px) {
  .sc-row {
    grid-template-columns: 1fr 1fr;
    grid-template-areas:
      'label label'
      'value vanilla'
      'delta delta';
    row-gap: 0.25rem;
  }
  .sc-label { grid-area: label; }
  .sc-value { grid-area: value; }
  .sc-vanilla { grid-area: vanilla; }
  .sc-delta { grid-area: delta; text-align: left; }
}
</style>