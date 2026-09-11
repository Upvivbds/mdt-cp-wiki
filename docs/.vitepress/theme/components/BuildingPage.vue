<script setup>
import { computed, onMounted, ref } from 'vue'
import { loadBuildings, toNum, fmtAny, starLabel } from '../composables/useRemoteData'

const props = defineProps({
  id: { type: String, default: '' },
  /** 构建期由页面 import 进来的完整记录；给了它就不再发请求 */
  building: { type: Object, default: null }
})

const fetched = ref(null)
const loading = ref(!props.building)
const error = ref('')

onMounted(async () => {
  // 数据已在构建期注入，无需再 fetch —— 首屏即有完整内容
  if (props.building) return
  try {
    const list = await loadBuildings()
    fetched.value = list.find((x) => x && x.id === props.id) || null
    if (!fetched.value) error.value = `没有找到 id 为「${props.id}」的建筑。`
  } catch (e) {
    error.value = e && e.message ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

const buildingData = computed(() => props.building || fetched.value)
const b = computed(() => buildingData.value || {})
const raw = computed(() => b.value.raw || {})
const packs = computed(() => (Array.isArray(b.value.packs) ? b.value.packs : []))

const nameZh = computed(() => b.value.nameZh || b.value.id || props.id)
const showEn = computed(() => !!b.value.nameZh && b.value.nameZh !== b.value.id)

const descParagraphs = computed(() => {
  const d = raw.value.description
  if (!d) return []
  return String(d)
    .split(/\r?\n+/)
    .map((s) => s.trim())
    .filter(Boolean)
})

/* ---------------- raw 字段拆分 ---------------- */

function isPlainObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v)
}

function isScalar(v) {
  return v === null || v === undefined || typeof v !== 'object'
}

const SCALAR_LABELS = {
  range: '射程',
  reload: '装填（tick）',
  itemCapacity: '物品容量',
  ammoCapacity: '弹药容量',
  shootWarmupSpeed: '预热速度',
  minWarmup: '最小预热',
  shootDuration: '开火时长',
  damage: '伤害',
  laserWidth: '激光宽度',
  statusDuration: '状态时长',
  retargetTime: '重新锁定时间',
  force: '推力',
  targetGround: '可攻击地面',
  placeableLiquid: '可放置于液体',
  placeableOn: '可放置于',
  consumePower: '耗电',
  size: '占地尺寸',
  health: '血量',
  armor: '护甲',
  baseExplosiveness: '基础爆炸性',
  status: '施加状态',
  shootType: '射击类型',
  scaleDamageEfficiency: '伤害缩放效率',
  maxHeatEfficiency: '最大热效率',
  moveWhileCharging: '充能时移动'
}

const scalarRows = computed(() =>
  Object.keys(raw.value)
    .filter((k) => isScalar(raw.value[k]) && raw.value[k] !== undefined)
    .map((k) => ({
      key: k,
      label: SCALAR_LABELS[k] || k,
      value: raw.value[k]
    }))
)

const arrayRows = computed(() =>
  Object.keys(raw.value)
    .filter((k) => Array.isArray(raw.value[k]))
    .map((k) => ({ key: k, label: SCALAR_LABELS[k] || k, value: raw.value[k] }))
)

/** ammoTypes：键可能是带引号的 \"silicon\"，显示时剥掉引号 */
const ammoRows = computed(() => {
  const at = raw.value.ammoTypes
  if (!isPlainObject(at)) return []
  return Object.keys(at).map((k) => {
    const v = at[k]
    const inner = isPlainObject(v) ? v : {}
    return {
      key: k,
      label: String(k).replace(/^["']|["']$/g, ''),
      type: inner.type || '',
      fields: Object.keys(inner)
        .filter((f) => isScalar(inner[f]))
        .map((f) => ({ key: f, label: SCALAR_LABELS[f] || f, value: inner[f] })),
      nested: Object.keys(inner)
        .filter((f) => isPlainObject(inner[f]))
        .map((f) => ({ key: f, obj: inner[f] }))
    }
  })
})

/** 嵌套对象（弹药里的 fragBullet 之类）转成可展示的扁平行 */
function nestedRows(obj) {
  if (!isPlainObject(obj)) return []
  return Object.keys(obj)
    .filter((f) => isScalar(obj[f]))
    .map((f) => ({ key: f, label: SCALAR_LABELS[f] || f, value: obj[f] }))
}

const rawJson = computed(() => {
  try {
    return JSON.stringify(raw.value, null, 2)
  } catch {
    return '(无法序列化 raw 数据)'
  }
})

const rawFieldCount = computed(() => Object.keys(raw.value).length)

/** 炮塔给一个粗略的每秒伤害参考：单发伤害 × 60 / 装填 */
const turretHint = computed(() => {
  const r = toNum(raw.value.reload)
  const d = toNum(raw.value.damage)
  if (r === null || r <= 0 || d === null) return null
  return (d * 60) / r
})
</script>

<template>
  <div class="building-page">
    <p v-if="loading" class="bp-hint">正在加载建筑数据…</p>
    <p v-else-if="error" class="bp-hint error">{{ error }}</p>

    <template v-else-if="buildingData">
      <header class="bp-header">
        <div class="bp-title">
          <h1>{{ nameZh }}</h1>
          <code v-if="showEn" class="bp-id">{{ b.id }}</code>
        </div>

        <div class="bp-badges">
          <span :class="['mz-badge', 'star-' + (b.star || '')]">
            {{ b.star || '?' }} · {{ starLabel(b.star) }}
          </span>
          <span v-if="b.author" class="mz-badge author">作者 {{ b.author }}</span>
          <span v-if="b.category" class="mz-badge">{{ b.category }}</span>
        </div>

        <div v-if="packs.length" class="bp-packs">
          <span class="bp-packs-label">所属补丁包</span>
          <ul>
            <li v-for="p in packs" :key="p">{{ p }}</li>
          </ul>
        </div>
      </header>

      <section v-if="descParagraphs.length" class="bp-section">
        <h2>简介</h2>
        <p v-for="(p, i) in descParagraphs" :key="i" class="bp-desc">{{ p }}</p>
      </section>

      <section v-if="scalarRows.length" class="bp-section">
        <h2>
          数据包改动参数
          <span class="bp-count">{{ scalarRows.length }} 项</span>
        </h2>
        <p class="bp-note">
          下表只列出数据包在这栋建筑上<strong>显式覆盖</strong>的字段；未列出的字段沿用原版数值。
        </p>
        <div class="bp-table">
          <div v-for="r in scalarRows" :key="r.key" class="bp-row">
            <span class="bp-k">{{ r.label }}</span>
            <code class="bp-raw-k">{{ r.key }}</code>
            <span class="bp-v mz-mono">{{ fmtAny(r.value) }}</span>
          </div>
        </div>
        <p v-if="turretHint !== null" class="bp-note">
          单发伤害 / 装填参考：约 <strong>{{ Math.round(turretHint * 100) / 100 }}</strong> 伤害每 tick
          （= {{ Math.round((turretHint * 60) * 100) / 100 }} / 秒，未计入溅射与多管齐射）。
        </p>
      </section>

      <section v-if="arrayRows.length" class="bp-section">
        <h2>列表参数</h2>
        <div v-for="r in arrayRows" :key="r.key" class="bp-array">
          <div class="bp-array-head">{{ r.label }} <code>{{ r.key }}</code></div>
          <ul>
            <li v-for="(v, i) in r.value" :key="i" class="mz-mono">{{ fmtAny(v) }}</li>
          </ul>
        </div>
      </section>

      <section v-if="ammoRows.length" class="bp-section">
        <h2>
          弹药类型
          <span class="bp-count">{{ ammoRows.length }} 种</span>
        </h2>
        <div class="bp-ammos">
          <div v-for="a in ammoRows" :key="a.key" class="bp-ammo">
            <div class="bp-ammo-head">
              <span class="bp-ammo-name">{{ a.label }}</span>
              <code v-if="a.type" class="bp-ammo-type">{{ a.type }}</code>
            </div>
            <table v-if="a.fields.length" class="bp-ammo-table">
              <tbody>
                <tr v-for="f in a.fields" :key="f.key">
                  <td class="k">{{ f.label }}</td>
                  <td class="v mz-mono">{{ fmtAny(f.value) }}</td>
                </tr>
              </tbody>
            </table>
            <div v-for="n in a.nested" :key="n.key" class="bp-ammo-nested">
              <div class="bp-ammo-nested-head">{{ n.key }}</div>
              <table class="bp-ammo-table">
                <tbody>
                  <tr v-for="f in nestedRows(n.obj)" :key="f.key">
                    <td class="k">{{ f.label }}</td>
                    <td class="v mz-mono">{{ fmtAny(f.value) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section class="bp-section">
        <h2>原始数据</h2>
        <details>
          <summary>展开查看该建筑的 raw JSON（共 {{ rawFieldCount }} 个顶层字段）</summary>
          <pre class="bp-raw"><code>{{ rawJson }}</code></pre>
        </details>
      </section>
    </template>
  </div>
</template>

<style scoped>
.building-page {
  margin-top: 0.5rem;
}

.bp-hint {
  color: var(--vp-c-text-3);
}

.bp-hint.error {
  color: #ff7b7b;
}

.bp-header {
  padding: 1rem 1.1rem;
  border: 1px solid var(--mz-border);
  border-radius: 14px;
  background: linear-gradient(150deg, var(--mz-surface-2), var(--mz-surface));
}

.bp-title {
  display: flex;
  align-items: baseline;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.bp-title h1 {
  margin: 0;
  padding: 0;
  border: none;
  font-size: 1.9rem;
  line-height: 1.2;
}

.bp-id {
  font-size: 0.85rem;
  color: var(--vp-c-text-3);
  background: var(--vp-code-bg);
  padding: 0.1rem 0.45rem;
  border-radius: 6px;
}

.bp-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.7rem;
}

.bp-packs {
  margin-top: 0.85rem;
  padding-top: 0.7rem;
  border-top: 1px solid var(--mz-border);
  font-size: 0.82rem;
}

.bp-packs-label {
  color: var(--vp-c-text-3);
}

.bp-packs ul {
  margin: 0.3rem 0 0;
  padding-left: 1.1rem;
  color: var(--vp-c-text-2);
}

.bp-section {
  margin-top: 1.8rem;
}

.bp-section h2 {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.bp-count {
  font-size: 0.72rem;
  font-weight: 400;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--mz-accent) 40%, transparent);
  color: var(--mz-accent);
}

.bp-note {
  font-size: 0.82rem;
  color: var(--vp-c-text-3);
  margin: 0.4rem 0 0.8rem;
}

.bp-note strong {
  color: var(--mz-accent);
  font-family: var(--vp-font-family-mono);
}

.bp-desc {
  color: var(--vp-c-text-2);
  line-height: 1.75;
}

.bp-table {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.bp-row {
  display: grid;
  grid-template-columns: 9rem minmax(8rem, 1fr) auto;
  gap: 0.6rem;
  align-items: center;
  padding: 0.45rem 0.7rem;
  border: 1px solid var(--mz-border);
  border-radius: 8px;
  background: var(--mz-surface);
  font-size: 0.88rem;
}

.bp-k {
  color: var(--vp-c-text-1);
  font-weight: 500;
}

.bp-raw-k {
  font-size: 0.75rem;
  color: var(--vp-c-text-3);
}

.bp-v {
  color: var(--mz-accent);
  font-weight: 600;
}

.bp-array {
  margin-bottom: 0.8rem;
  padding: 0.7rem 0.85rem;
  border: 1px solid var(--mz-border);
  border-radius: 10px;
  background: var(--mz-surface);
}

.bp-array-head {
  font-size: 0.88rem;
  color: var(--vp-c-text-1);
  margin-bottom: 0.35rem;
}

.bp-array-head code {
  font-size: 0.75rem;
  color: var(--vp-c-text-3);
}

.bp-array ul {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.8rem;
  color: var(--vp-c-text-2);
}

.bp-ammos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr));
  gap: 0.7rem;
}

.bp-ammo {
  padding: 0.75rem 0.85rem;
  border: 1px solid var(--mz-border);
  border-radius: 10px;
  background: var(--mz-surface);
}

.bp-ammo-head {
  display: flex;
  align-items: baseline;
  gap: 0.45rem;
  flex-wrap: wrap;
  margin-bottom: 0.45rem;
}

.bp-ammo-name {
  font-weight: 700;
  color: var(--mz-accent);
  font-family: var(--vp-font-family-mono);
  font-size: 0.92rem;
}

.bp-ammo-type {
  font-size: 0.72rem;
  color: var(--vp-c-text-3);
}

.bp-ammo-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.bp-ammo-table td {
  padding: 0.15rem 0;
  border: none;
  vertical-align: top;
}

.bp-ammo-table td.k {
  color: var(--vp-c-text-3);
  width: 48%;
  word-break: break-all;
}

.bp-ammo-table td.v {
  color: var(--vp-c-text-1);
  word-break: break-all;
}

.bp-ammo-nested {
  margin-top: 0.5rem;
  padding-top: 0.45rem;
  border-top: 1px dashed var(--mz-border);
}

.bp-ammo-nested-head {
  font-size: 0.74rem;
  color: var(--vp-c-text-3);
  font-family: var(--vp-font-family-mono);
  margin-bottom: 0.25rem;
}

.bp-raw {
  max-height: 32rem;
  overflow: auto;
  margin: 0.75rem 0 0;
  font-size: 0.76rem;
  line-height: 1.55;
}

@media (max-width: 640px) {
  .bp-row {
    grid-template-columns: 1fr auto;
    grid-template-areas:
      'label value'
      'raw raw';
  }
  .bp-k { grid-area: label; }
  .bp-v { grid-area: value; text-align: right; }
  .bp-raw-k { grid-area: raw; }
}
</style>