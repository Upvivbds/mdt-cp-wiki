<script setup>
import { computed, ref } from 'vue'
import { toNum, fmtNum } from '../composables/useRemoteData'

const props = defineProps({
  unit: { type: Object, default: () => ({}) }
})

/* ---------------- 参数 ---------------- */
const reloadMult = ref(1)
const damageMult = ref(1)
const target = ref('all') // all | air | ground

const TARGETS = [
  { key: 'all', label: '全部' },
  { key: 'air', label: '只算对空' },
  { key: 'ground', label: '只算对地' }
]

function reset() {
  reloadMult.value = 1
  damageMult.value = 1
  target.value = 'all'
}

const dirty = computed(
  () => reloadMult.value !== 1 || damageMult.value !== 1 || target.value !== 'all'
)

/* ---------------- 数据容错 ---------------- */
const weapons = computed(() => (Array.isArray(props.unit && props.unit.weapons) ? props.unit.weapons : []))
const dps = computed(() => (props.unit && props.unit.dps) || {})
const isSuicide = computed(() => !!(props.unit && props.unit.dps && props.unit.dps.suicide))
// 人工校准备注：静态解析算不出的单位，值由 up 手测给出
const manualNote = computed(() => (props.unit && props.unit.dps && props.unit.dps.manual) || '')
const vanillaDps = computed(() => (props.unit && props.unit.vanillaDps) || {})

const canAir = (w) =>
  w && w.canHitAir !== undefined && w.canHitAir !== null
    ? !!w.canHitAir
    : !!(w && w.collidesAir)

const canGround = (w) =>
  w && w.canHitGround !== undefined && w.canHitGround !== null
    ? !!w.canHitGround
    : !!(w && w.collidesGround)

const CONTINUOUS_TYPES = [
  'PointLaserBulletType',
  'ContinuousLaserBulletType',
  'ContinuousFlameBulletType'
]

function isContinuous(w) {
  if (!w) return false
  if (w.continuous === true) return true
  return CONTINUOUS_TYPES.includes(w.bulletType)
}

/**
 * 常规武器：DPS = shots × damage × 60 / reload
 * 持续光束：DPS = damage / damageInterval × 60
 * reload / damageInterval 单位是 tick，60 tick = 1 秒。
 * 装填时间倍率 reloadMult 视为「射速倍率」：有效 tick 数 = 原值 / reloadMult。
 */
function calcWeaponDps(w) {
  if (!w) return 0
  const dmg = (toNum(w.damage) || 0) * damageMult.value
  const rm = reloadMult.value > 0 ? reloadMult.value : 0.0001

  if (isContinuous(w)) {
    const di = toNum(w.damageInterval) !== null ? toNum(w.damageInterval) : toNum(w.reload)
    if (di === null || di <= 0) return 0
    const eff = di / rm
    if (eff <= 0) return 0
    return (dmg / eff) * 60
  }

  const reload = toNum(w.reload)
  if (reload === null || reload <= 0) return 0
  const shots = toNum(w.shots) !== null ? toNum(w.shots) : 1
  const eff = reload / rm
  if (eff <= 0) return 0
  return (shots * dmg * 60) / eff
}

function calcSplashDps(w) {
  if (!w || isContinuous(w)) return 0
  const sd = toNum(w.splashDamage) || 0
  if (sd <= 0) return 0
  const reload = toNum(w.reload)
  if (reload === null || reload <= 0) return 0
  const shots = toNum(w.shots) !== null ? toNum(w.shots) : 1
  const rm = reloadMult.value > 0 ? reloadMult.value : 0.0001
  return (shots * sd * damageMult.value * 60) / (reload / rm)
}

const rows = computed(() =>
  weapons.value.map((w, i) => {
    const cont = isContinuous(w)
    return {
      key: `${(w && w.name) || 'weapon'}-${i}`,
      index: i + 1,
      name: (w && w.name) || '（未命名）',
      bulletType: (w && w.bulletType) || '—',
      mode: (w && w.mode) || (cont ? 'continuous' : '—'),
      reload: toNum(w && w.reload),
      reloadSec: toNum(w && w.reloadSec),
      shots: toNum(w && w.shots) !== null ? toNum(w && w.shots) : 1,
      damage: toNum(w && w.damage),
      splashDamage: toNum(w && w.splashDamage) || 0,
      splashRadius: toNum(w && w.splashDamageRadius),
      continuous: cont,
      air: canAir(w),
      ground: canGround(w),
      calcDps: calcWeaponDps(w),
      calcSplashDps: calcSplashDps(w),
      origDps: toNum(w && w.dps),
      origSplashDps: toNum(w && w.splashDps)
    }
  })
)

const activeRows = computed(() => {
  const t = target.value
  return rows.value.filter((r) => (t === 'all' ? true : t === 'air' ? r.air : r.ground))
})

const sum = (list, pick) => list.reduce((s, r) => s + (Number.isFinite(pick(r)) ? pick(r) : 0), 0)

const calcTotal = computed(() => sum(activeRows.value, (r) => r.calcDps))
const calcSplashTotal = computed(() => sum(activeRows.value, (r) => r.calcSplashDps))
const calcAir = computed(() => sum(rows.value.filter((r) => r.air), (r) => r.calcDps))
const calcGround = computed(() => sum(rows.value.filter((r) => r.ground), (r) => r.calcDps))
const calcAirSplash = computed(() => sum(rows.value.filter((r) => r.air), (r) => r.calcSplashDps))
const calcGroundSplash = computed(() => sum(rows.value.filter((r) => r.ground), (r) => r.calcSplashDps))

const origDirect = computed(() => {
  const d = toNum(dps.value.direct)
  return d !== null ? d : toNum(dps.value.total)
})
const origSplash = computed(() => toNum(dps.value.splash))
const origAir = computed(() => toNum(dps.value.air))
const origGround = computed(() => toNum(dps.value.ground))
const origVanillaTotal = computed(() => toNum(vanillaDps.value.total))
const origVanillaSplash = computed(() => toNum(vanillaDps.value.splash))
const origVanillaAir = computed(() => toNum(vanillaDps.value.air))
const origVanillaGround = computed(() => toNum(vanillaDps.value.ground))

const origGrp = computed(() => toNum(dps.value && dps.value.grpTotal))
const origSingleTotal = computed(() => toNum(dps.value && dps.value.total))

const bigCards = computed(() => [
  {
    label: '群体 DPS',
    value: dirty.value ? calcTotal.value : origGrp.value || calcTotal.value,
    hint: '完整游戏模型：含穿透 / 激光 / 闪电的多目标倍率、溅射按 0.75 折算',
    sub: [
      origGrp.value && origSingleTotal.value
        ? `对单口径 ${fmtNum(origSingleTotal.value)}`
        : null
    ].filter(Boolean)
  },
  {
    label: '单体 DPS',
    value: dirty.value ? calcTotal.value : origDirect.value !== null ? origDirect.value : calcTotal.value,
    hint: dirty.value
      ? '按当前参数实时计算'
      : origDirect.value !== null
        ? '数据包解析值（含分裂子弹）'
        : '按公式计算',
    sub: [
      origVanillaTotal.value !== null ? `原版单体 ${fmtNum(origVanillaTotal.value)}` : null
    ].filter(Boolean)
  },
  {
    label: '范围 DPS',
    value: dirty.value
      ? calcSplashTotal.value
      : origSplash.value !== null
        ? origSplash.value
        : calcSplashTotal.value,
    hint: '溅射伤害，与单体分开计',
    sub: [
      origVanillaSplash.value !== null ? `原版范围 ${fmtNum(origVanillaSplash.value)}` : null
    ].filter(Boolean)
  },
  {
    label: '对空 DPS',
    value: dirty.value ? calcAir.value : origAir.value !== null ? origAir.value : calcAir.value,
    hint: dirty.value ? '实时计算' : '数据包解析值',
    sub: [
      origVanillaAir.value !== null ? `原版 ${fmtNum(origVanillaAir.value)}` : null,
      calcAirSplash.value > 0 ? `溅射 ${fmtNum(calcAirSplash.value)}` : null
    ].filter(Boolean)
  },
  {
    label: '对地 DPS',
    value: dirty.value ? calcGround.value : origGround.value !== null ? origGround.value : calcGround.value,
    hint: dirty.value ? '实时计算' : '数据包解析值',
    sub: [
      origVanillaGround.value !== null ? `原版 ${fmtNum(origVanillaGround.value)}` : null,
      calcGroundSplash.value > 0 ? `溅射 ${fmtNum(calcGroundSplash.value)}` : null
    ].filter(Boolean)
  }
])
</script>

<template>
  <div class="dps-panel">
    <p v-if="manualNote" class="dps-manual-note">
      <strong>手测值</strong> —— {{ manualNote }}
    </p>
    <p v-if="isSuicide" class="dps-suicide-note">
      殉爆单位：伤害来自单位死亡时的爆炸，没有持续输出的概念，因此不计 DPS。
      单发爆炸伤害见下方武器明细。
    </p>
    <div class="dps-big">
      <div v-for="c in bigCards" :key="c.label" class="dps-big-card">
        <div class="dps-big-label">{{ c.label }}</div>
        <div class="dps-big-value">{{ fmtNum(c.value) }}</div>
        <div class="dps-big-hint">{{ c.hint }}</div>
        <div v-if="c.sub.length" class="dps-big-sub">
          <span v-for="s in c.sub" :key="s">{{ s }}</span>
        </div>
      </div>
    </div>

    <!-- DPS 计算器 -->
    <div class="dps-calc">
      <div class="dps-calc-head">
        <strong>DPS 计算器</strong>
        <span class="dps-calc-note">
          常规武器 <code>DPS = shots × damage × 60 / reload</code>；持续光束
          <code>DPS = damage / damageInterval × 60</code>（60 tick = 1 秒，溅射不计入单体 DPS）
        </span>
      </div>

      <div class="dps-calc-controls">
        <label class="dps-ctrl">
          <span>射速倍率（装填时间 ÷ 该值）</span>
          <input v-model.number="reloadMult" type="number" min="0.05" max="20" step="0.05" />
        </label>
        <label class="dps-ctrl">
          <span>伤害倍率</span>
          <input v-model.number="damageMult" type="number" min="0.05" max="20" step="0.05" />
        </label>
        <div class="dps-ctrl">
          <span>目标类型</span>
          <div class="dps-targets">
            <button
              v-for="t in TARGETS"
              :key="t.key"
              type="button"
              :class="['dps-tab', { active: target === t.key }]"
              @click="target = t.key"
            >
              {{ t.label }}
            </button>
          </div>
        </div>
        <button type="button" class="dps-reset" :disabled="!dirty" @click="reset">重置</button>
      </div>

      <div class="dps-calc-result">
        当前筛选（{{ TARGETS.find((t) => t.key === target)?.label }}）合计：
        <strong>{{ fmtNum(calcTotal) }}</strong> DPS
        <span v-if="calcSplashTotal > 0" class="dps-calc-splash">
          （另有溅射 {{ fmtNum(calcSplashTotal) }} DPS，不计入单体）
        </span>
      </div>
    </div>

    <!-- 武器明细 -->
    <div v-if="rows.length" class="dps-table-wrap">
      <table class="dps-table">
        <thead>
          <tr>
            <th>#</th>
            <th>武器</th>
            <th>弹种 / 模式</th>
            <th>装填</th>
            <th>每轮发数</th>
            <th>单发伤害</th>
            <th>单武器 DPS</th>
            <th>溅射 DPS</th>
            <th>可打</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.key" :class="{ 'is-off': target !== 'all' && !activeRows.includes(r) }">
            <td class="mono">{{ r.index }}</td>
            <td>{{ r.name }}</td>
            <td class="mono small">
              {{ r.bulletType }}<br /><span class="muted">{{ r.mode }}{{ r.continuous ? ' · 连续' : '' }}</span>
            </td>
            <td class="mono">
              {{ r.reload !== null ? `${r.reload} tick` : '—' }}
              <span v-if="r.reloadSec !== null" class="muted small">（{{ fmtNum(r.reloadSec, 3) }}s）</span>
            </td>
            <td class="mono">{{ r.shots }}</td>
            <td class="mono">{{ r.damage !== null ? fmtNum(r.damage) : '—' }}</td>
            <td class="mono strong">{{ fmtNum(r.calcDps) }}</td>
            <td class="mono">
              <span v-if="r.calcSplashDps > 0">
                {{ fmtNum(r.calcSplashDps) }}
                <span class="muted small">（半径 {{ r.splashRadius }}）</span>
              </span>
              <span v-else class="muted">—</span>
            </td>
            <td class="small">
              <span :class="['tag', r.air ? 'on' : 'off']">空</span>
              <span :class="['tag', r.ground ? 'on' : 'off']">地</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else class="dps-empty">该单位没有解析出武器数据。</p>
  </div>
</template>

<style scoped>
.dps-panel {
  margin: 1rem 0 1.5rem;
}

.dps-big {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.dps-big-card {
  padding: 0.9rem 1rem;
  border-radius: 12px;
  border: 1px solid var(--mz-border);
  background: linear-gradient(160deg, color-mix(in srgb, var(--mz-accent) 10%, var(--mz-surface)), var(--mz-surface));
}

.dps-big-label {
  font-size: 0.85rem;
  color: var(--vp-c-text-3);
  letter-spacing: 0.05em;
}

.dps-big-value {
  font-family: var(--vp-font-family-mono);
  font-size: 1.9rem;
  font-weight: 700;
  line-height: 1.2;
  color: var(--mz-accent);
}

.dps-big-hint,
.dps-big-sub {
  font-size: 0.78rem;
  color: var(--vp-c-text-3);
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.dps-calc {
  margin-top: 1rem;
  padding: 0.9rem 1rem;
  border-radius: 12px;
  border: 1px dashed var(--mz-border-strong);
  background: var(--mz-surface);
}

.dps-calc-head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: baseline;
}

.dps-calc-note {
  font-size: 0.78rem;
  color: var(--vp-c-text-3);
}

.dps-calc-note code {
  font-size: 0.75rem;
}

.dps-calc-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem;
  align-items: flex-end;
  margin-top: 0.75rem;
}

.dps-ctrl {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.8rem;
  color: var(--vp-c-text-2);
}

.dps-ctrl input {
  width: 9rem;
  padding: 0.3rem 0.5rem;
  border-radius: 6px;
  border: 1px solid var(--mz-border-strong);
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  font-family: var(--vp-font-family-mono);
}

.dps-targets {
  display: flex;
  gap: 0.25rem;
}

.dps-tab {
  padding: 0.3rem 0.6rem;
  border-radius: 6px;
  border: 1px solid var(--mz-border-strong);
  background: transparent;
  color: var(--vp-c-text-2);
  font-size: 0.8rem;
  cursor: pointer;
}

.dps-tab.active {
  border-color: var(--mz-accent);
  color: var(--mz-accent);
  background: color-mix(in srgb, var(--mz-accent) 14%, transparent);
}

.dps-reset {
  padding: 0.32rem 0.8rem;
  border-radius: 6px;
  border: 1px solid var(--mz-border-strong);
  background: transparent;
  color: var(--vp-c-text-2);
  font-size: 0.8rem;
  cursor: pointer;
}

.dps-reset:disabled {
  opacity: 0.4;
  cursor: default;
}

.dps-calc-result {
  margin-top: 0.7rem;
  font-size: 0.9rem;
  color: var(--vp-c-text-2);
}

.dps-calc-result strong {
  color: var(--mz-accent);
  font-family: var(--vp-font-family-mono);
  font-size: 1.1rem;
}

.dps-calc-splash {
  font-size: 0.8rem;
  color: var(--vp-c-text-3);
}

.dps-table-wrap {
  margin-top: 1rem;
  overflow-x: auto;
}

.dps-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.dps-table th,
.dps-table td {
  padding: 0.45rem 0.55rem;
  border-bottom: 1px solid var(--mz-border);
  text-align: left;
  vertical-align: top;
}

.dps-table th {
  color: var(--vp-c-text-3);
  font-weight: 500;
  white-space: nowrap;
}

.dps-table tr.is-off {
  opacity: 0.4;
}

.mono {
  font-family: var(--vp-font-family-mono);
}

.small {
  font-size: 0.78rem;
}

.muted {
  color: var(--vp-c-text-3);
}

.strong {
  color: var(--mz-accent);
  font-weight: 700;
}

.tag {
  display: inline-block;
  min-width: 1.2rem;
  text-align: center;
  margin-right: 0.2rem;
  padding: 0 0.25rem;
  border-radius: 4px;
  border: 1px solid var(--mz-border-strong);
  font-size: 0.75rem;
}

.tag.on {
  color: #3ddc97;
  border-color: color-mix(in srgb, #3ddc97 50%, transparent);
}

.tag.off {
  color: var(--vp-c-text-3);
  opacity: 0.6;
}

.dps-empty {
  color: var(--vp-c-text-3);
  font-size: 0.9rem;
}

@media (max-width: 720px) {
  .dps-big {
    grid-template-columns: 1fr;
  }
}

.dps-manual-note {
  margin: 0 0 0.75rem;
  padding: 0.55rem 0.75rem;
  border-left: 3px solid var(--mz-accent-2, #ffa53d);
  background: rgba(255, 165, 61, 0.10);
  border-radius: 0 6px 6px 0;
  font-size: 0.85rem;
  color: var(--vp-c-text-2);
}

.dps-suicide-note {
  margin: 0 0 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(255, 123, 114, 0.4);
  border-left: 3px solid var(--mz-bad);
  border-radius: 8px;
  background: rgba(255, 123, 114, 0.08);
  font-size: 0.84rem;
  line-height: 1.7;
  color: var(--vp-c-text-2);
}
</style>