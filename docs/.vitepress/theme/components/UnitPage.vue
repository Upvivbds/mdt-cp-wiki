<script setup>
import { computed, onMounted, ref } from 'vue'
import spriteManifest from '../../../data/sprites.json'
import StatCompare from './StatCompare.vue'
import DpsPanel from './DpsPanel.vue'
import { fmtAny, loadUnits, starLabel, toNum, unitSprite } from '../composables/useRemoteData'

const props = defineProps({
  id: { type: String, default: '' },
  /** 构建期由页面 import 进来的完整记录；给了它就不再发请求 */
  unit: { type: Object, default: null }
})

const fetched = ref(null)
const loading = ref(!props.unit)
const error = ref('')

onMounted(async () => {
  // 数据已在构建期注入，无需再 fetch —— 首屏即有完整内容
  if (props.unit) return
  try {
    const list = await loadUnits()
    fetched.value = list.find((x) => x && x.id === props.id) || null
    if (!fetched.value) error.value = `没有找到 id 为「${props.id}」的单位。`
  } catch (e) {
    error.value = e && e.message ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

const UNIT_SPRITES = new Set(spriteManifest.units || [])
const hasUnitSprite = computed(() => UNIT_SPRITES.has((u.value && u.value.id) || ''))

const unit = computed(() => props.unit || fetched.value)

const u = computed(() => unit.value || {})
const stats = computed(() => u.value.stats || {})
const vanilla = computed(() => u.value.vanillaStats || {})
const packs = computed(() => (Array.isArray(u.value.packs) ? u.value.packs : []))
const weapons = computed(() => (Array.isArray(u.value.weapons) ? u.value.weapons : []))
const abilities = computed(() => (Array.isArray(u.value.abilities) ? u.value.abilities : []))
const parts = computed(() => (Array.isArray(u.value.parts) ? u.value.parts : []))

/** description 里的 \n 渲染成段落 */
const descParagraphs = computed(() => {
  const d = u.value.description
  if (!d) return []
  return String(d)
    .split(/\r?\n+/)
    .map((s) => s.trim())
    .filter(Boolean)
})

const nameZh = computed(() => u.value.nameZh || u.value.id || props.id)
const showEn = computed(() => !!u.value.nameZh && u.value.nameZh !== u.value.id)

const rawJson = computed(() => {
  try {
    return JSON.stringify(u.value.raw || {}, null, 2)
  } catch {
    return '(无法序列化 raw 数据)'
  }
})
const rawOpen = ref(false)

/** 数值型属性行定义 */
const STAT_ROWS = [
  { key: 'health', label: '血量', higherIsBetter: true, digits: 0 },
  { key: 'armor', label: '护甲', higherIsBetter: true, digits: 0 },
  { key: 'speed', label: '移动速度', higherIsBetter: true, digits: 2 },
  { key: 'hitSize', label: '碰撞体积', higherIsBetter: true, neutral: true, digits: 0 },
  { key: 'range', label: '射程', higherIsBetter: true, digits: 0 },
  { key: 'maxRange', label: '最大射程', higherIsBetter: true, digits: 0 },
  { key: 'fogRadius', label: '视野半径', higherIsBetter: true, digits: 0 },
  { key: 'payloadCapacity', label: '载荷容量', higherIsBetter: true, digits: 0 }
]

/** 只保留「数据包或原版至少有一边有值」的属性行 */
const statRows = computed(() =>
  STAT_ROWS.filter((r) => {
    const a = stats.value[r.key]
    const b = vanilla.value[r.key]
    return (a !== null && a !== undefined && a !== '') || (b !== null && b !== undefined && b !== '')
  })
)

const boolRows = computed(() =>
  [
    { key: 'targetAir', label: '可攻击空中' },
    { key: 'targetGround', label: '可攻击地面' }
  ].filter((r) => stats.value[r.key] !== null && stats.value[r.key] !== undefined)
)

/** 统计有多少项被改动 */
const diffCount = computed(
  () =>
    statRows.value.filter((r) => {
      const a = toNum(stats.value[r.key])
      const b = toNum(vanilla.value[r.key])
      if (a === null || b === null) return false
      return a !== b
    }).length
)

const ABILITY_LABELS = {
  ForceFieldAbility: '力场',
  StatusFieldAbility: '状态场',
  ShieldArcAbility: '弧形护盾',
  EnergyFieldAbility: '能量场',
  ShieldRegenFieldAbility: '护盾回复场',
  RepairFieldAbility: '维修场',
  UnitSpawnAbility: '单位生成',
  SpawnDeathAbility: '死亡生成'
}

/** 把 ability 对象的字段转成 [label, value] 列表，跳过 type */
function abilityEntries(a) {
  if (!a || typeof a !== 'object') return []
  return Object.keys(a)
    .filter((k) => k !== 'type')
    .map((k) => [k, fmtAny(a[k])])
}

function abilityTitle(a, i) {
  const t = a && a.type
  if (!t) return `能力 ${i + 1}（未标注类型）`
  return `${ABILITY_LABELS[t] || t}`
}

function weaponTargets(w) {
  const air = w && w.canHitAir !== null && w.canHitAir !== undefined ? w.canHitAir : w && w.collidesAir
  const ground =
    w && w.canHitGround !== null && w.canHitGround !== undefined ? w.canHitGround : w && w.collidesGround
  return { air: !!air, ground: !!ground }
}
</script>

<template>
  <div class="unit-page">
    <p v-if="loading" class="up-hint">正在加载单位数据…</p>
    <p v-else-if="error" class="up-hint error">{{ error }}</p>

    <template v-else-if="unit">
      <!-- 头部 -->
      <header class="up-header">
    <img class="up-sprite" v-if="hasUnitSprite" :src="unitSprite(u.id)" alt="" loading="lazy" onerror="this.style.display='none'" />
        <div class="up-title">
          <h1>{{ nameZh }}</h1>
          <code v-if="showEn" class="up-id">{{ u.id }}</code>
        </div>

        <div class="up-badges">
          <span v-if="u.dps && u.dps.suicide" class="mz-badge suicide" title="伤害来自死亡时的爆炸，无持续输出">
            殉爆单位
          </span>
          <span :class="['mz-badge', 'star-' + (u.star || '')]">
            {{ u.star || '?' }} · {{ starLabel(u.star) }}
          </span>
          <span v-if="u.author" class="mz-badge author">作者 {{ u.author }}</span>
          <span v-if="u.categoryLabel || u.category" class="mz-badge">
            {{ u.categoryLabel || u.category }}
          </span>
          <span v-if="u.tier !== null && u.tier !== undefined" class="mz-badge tier">T{{ u.tier }} 级</span>
          <span v-if="u.unitClass" class="mz-badge mz-mono">{{ u.unitClass }}</span>
        </div>

        <div v-if="packs.length" class="up-packs">
          <span class="up-packs-label">所属补丁包</span>
          <ul>
            <li v-for="p in packs" :key="p">{{ p }}</li>
          </ul>
        </div>
      </header>

      <EffectChips kind="unit" :id="u.id || id" />

      <!-- 描述 -->
      <section v-if="descParagraphs.length" class="up-section">
        <h2>简介</h2>
        <p v-for="(p, i) in descParagraphs" :key="i" class="up-desc">{{ p }}</p>
      </section>

      <!-- 属性对比 -->
      <section class="up-section">
        <h2>
          属性对比
          <span v-if="diffCount" class="up-diff-tag">{{ diffCount }} 项有改动</span>
          <span v-else class="up-same-tag">与原版一致</span>
        </h2>
        <div class="up-cmp-head">
          <div>属性</div>
          <div>数据包</div>
          <div>原版</div>
          <div>差值</div>
        </div>
        <StatCompare
          v-for="r in statRows"
          :key="r.key"
          :label="r.label"
          :value="stats[r.key]"
          :vanilla="vanilla[r.key]"
          :higher-is-better="r.higherIsBetter !== false"
          :neutral="!!r.neutral"
          :digits="r.digits"
        />

        <div v-if="boolRows.length" class="up-bools">
          <div v-for="r in boolRows" :key="r.key" class="up-bool">
            <span>{{ r.label }}</span>
            <strong>{{ fmtAny(stats[r.key]) }}</strong>
          </div>
        </div>
      </section>

      <!-- DPS -->
      <section class="up-section">
        <h2>DPS 数据</h2>
        <DpsPanel :unit="u" />
      </section>

      <!-- 武器速览 -->
      <section v-if="weapons.length" class="up-section">
        <h2>武器概览</h2>
        <div class="up-weapons">
          <div v-for="(w, i) in weapons" :key="i" class="up-weapon">
            <div class="up-weapon-head">
              <span class="up-weapon-name">{{ w.name || '（未命名）' }}</span>
              <code class="up-weapon-type">{{ w.bulletType || '—' }}</code>
            </div>
            <div class="up-weapon-badges">
              <span v-if="w.mode" class="mz-badge">{{ w.mode }}</span>
              <span v-if="w.continuous" class="mz-badge tier">持续</span>
              <span :class="['mz-badge', weaponTargets(w).air ? 'star-S' : '']">
                对空 {{ weaponTargets(w).air ? '✓' : '✗' }}
              </span>
              <span :class="['mz-badge', weaponTargets(w).ground ? 'star-E' : '']">
                对地 {{ weaponTargets(w).ground ? '✓' : '✗' }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- 能力 -->
      <section v-if="abilities.length" class="up-section">
        <h2>能力</h2>
        <div class="up-abilities">
          <div v-for="(a, i) in abilities" :key="i" class="up-ability">
            <div class="up-ability-title">{{ abilityTitle(a, i) }}</div>
            <table v-if="abilityEntries(a).length" class="up-ability-table">
              <tbody>
                <tr v-for="[k, v] in abilityEntries(a)" :key="k">
                  <td class="k">{{ k }}</td>
                  <td class="v mz-mono">{{ v }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="up-ability-empty">（该能力没有可显示的字段）</p>
          </div>
        </div>
      </section>

      <!-- 部件 -->
      <section v-if="parts.length" class="up-section">
        <h2>部件（parts）</h2>
        <ul class="up-parts">
          <li v-for="(p, i) in parts" :key="i" class="mz-mono">{{ fmtAny(p) }}</li>
        </ul>
      </section>

      <!-- 原始数据 -->
      <section class="up-section">
        <h2>原始数据</h2>
        <details :open="rawOpen" @toggle="rawOpen = $event.target.open">
          <summary>展开查看合并后的 raw JSON（共 {{ Object.keys(u.raw || {}).length }} 个顶层字段）</summary>
          <pre class="up-raw"><code>{{ rawJson }}</code></pre>
        </details>
      </section>
    </template>
  </div>
</template>

<style scoped>
.unit-page {
  margin-top: 0.5rem;
}

.up-hint {
  color: var(--vp-c-text-3);
}

.up-hint.error {
  color: #ff7b7b;
}

.up-header {
  position: relative;
  padding-right: 7rem;
  padding: 1rem 1.1rem;
  border: 1px solid var(--mz-border);
  border-radius: 14px;
  background: linear-gradient(150deg, var(--mz-surface-2), var(--mz-surface));
}

.up-title {
  display: flex;
  align-items: baseline;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.up-title h1 {
  margin: 0;
  padding: 0;
  border: none;
  font-size: 1.9rem;
  line-height: 1.2;
}

.up-id {
  font-size: 0.85rem;
  color: var(--vp-c-text-3);
  background: var(--vp-code-bg);
  padding: 0.1rem 0.45rem;
  border-radius: 6px;
}

.up-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.7rem;
}

.up-packs {
  margin-top: 0.85rem;
  padding-top: 0.7rem;
  border-top: 1px solid var(--mz-border);
  font-size: 0.82rem;
}

.up-packs-label {
  color: var(--vp-c-text-3);
}

.up-packs ul {
  margin: 0.3rem 0 0;
  padding-left: 1.1rem;
  color: var(--vp-c-text-2);
}

.up-section {
  margin-top: 1.8rem;
}

.up-section h2 {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.up-diff-tag,
.up-same-tag {
  font-size: 0.72rem;
  font-weight: 400;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  border: 1px solid currentColor;
}

.up-diff-tag {
  color: var(--mz-accent-2);
}

.up-same-tag {
  color: var(--vp-c-text-3);
}

.up-desc {
  color: var(--vp-c-text-2);
  line-height: 1.75;
}

.up-cmp-head {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr 1.4fr;
  gap: 0.5rem;
  padding: 0 0.75rem 0.35rem;
  font-size: 0.75rem;
  color: var(--vp-c-text-3);
}

.up-cmp-head > div:last-child {
  text-align: right;
}

.up-bools {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.up-bool {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.4rem 0.7rem;
  border: 1px solid var(--mz-border);
  border-radius: 8px;
  background: var(--mz-surface);
  font-size: 0.85rem;
}

.up-bool span {
  color: var(--vp-c-text-3);
}

.up-bool strong {
  color: var(--mz-accent);
}

.up-weapons {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: 0.65rem;
}

.up-weapon {
  padding: 0.7rem 0.8rem;
  border: 1px solid var(--mz-border);
  border-radius: 10px;
  background: var(--mz-surface);
}

.up-weapon-head {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.up-weapon-name {
  font-weight: 600;
  color: var(--vp-c-text-1);
  font-size: 0.92rem;
}

.up-weapon-type {
  font-size: 0.74rem;
  color: var(--vp-c-text-3);
}

.up-weapon-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.5rem;
}

.up-abilities {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
  gap: 0.7rem;
}

.up-ability {
  padding: 0.75rem 0.85rem;
  border: 1px solid var(--mz-border);
  border-radius: 10px;
  background: var(--mz-surface);
}

.up-ability-title {
  font-weight: 600;
  color: var(--mz-accent);
  margin-bottom: 0.45rem;
  font-size: 0.92rem;
}

.up-ability-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.up-ability-table td {
  padding: 0.15rem 0;
  border: none;
  vertical-align: top;
}

.up-ability-table td.k {
  color: var(--vp-c-text-3);
  width: 42%;
  word-break: break-all;
}

.up-ability-table td.v {
  color: var(--vp-c-text-1);
  word-break: break-all;
}

.up-ability-empty {
  font-size: 0.8rem;
  color: var(--vp-c-text-3);
  margin: 0;
}

.up-parts {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.82rem;
  color: var(--vp-c-text-2);
}

.up-raw {
  max-height: 32rem;
  overflow: auto;
  margin: 0.75rem 0 0;
  font-size: 0.76rem;
  line-height: 1.55;
}

@media (max-width: 640px) {
  .up-cmp-head {
    display: none;
  }
}

.up-sprite {
  position: absolute;
  top: 1.1rem;
  right: 1.2rem;
  width: 96px;
  height: 96px;
  object-fit: contain;
  image-rendering: pixelated;
  opacity: 0.95;
  filter: drop-shadow(0 0 14px rgba(79, 209, 197, 0.35));
  pointer-events: none;
}

@media (max-width: 640px) {
  .up-sprite {
    width: 64px;
    height: 64px;
    opacity: 0.5;
  }
}

.up-badges .mz-badge.suicide {
  color: #ff7b72;
  border-color: rgba(255, 123, 114, 0.5);
  background: rgba(255, 123, 114, 0.12);
  font-weight: 600;
}
</style>