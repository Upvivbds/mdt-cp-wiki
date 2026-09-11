<script setup>
import { computed } from 'vue'
import { unitUrl, buildingUrl } from '../composables/useRemoteData'

const props = defineProps({
  effect: { type: Object, required: true },
  /** 全部状态效果的名单，用于「对立状态」互相跳转 */
  effects: { type: Array, default: () => [] }
})

const e = computed(() => props.effect || {})

const nameZh = computed(() => e.value.nameZh || e.value.id || '未知状态')
const hexColor = computed(() => {
  const c = String(e.value.color || '').replace(/^#/, '')
  return /^[0-9a-fA-F]{6,8}$/.test(c) ? '#' + c.slice(0, 6) : null
})

const mods = computed(() => e.value.mods || [])
const flags = computed(() => e.value.flags || [])
const appliers = computed(() => e.value.appliers || [])

/** 把 -15 显示成 -15%；正数补个 + 号，读起来更像增益/减益。 */
function pct(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return (n > 0 ? '+' : '') + n + '%'
}

function modClass(v) {
  const n = Number(v)
  if (!Number.isFinite(n) || n === 0) return 'flat'
  return n > 0 ? 'up' : 'down'
}

/** 对立状态里能对上本 wiki 条目的就给链接，否则只能按原版 id 显示。 */
function oppositeLink(id) {
  const hit = (props.effects || []).find((x) => x.id === id)
  return hit ? `/effects/${id}` : null
}

const kindLabel = { block: '建筑', unit: '单位' }
</script>

<template>
  <div class="effect-page">
    <header class="eh">
      <div class="eh-swatch" :style="hexColor ? { background: hexColor } : {}" />
      <div class="eh-text">
        <h1>{{ nameZh }}</h1>
        <p class="eh-id">
          <code>status.{{ e.id }}</code>
          <span v-if="!e.show" class="eh-hidden">游戏内不显示图标</span>
        </p>
      </div>
    </header>

    <section class="card">
      <h2>状态修正</h2>
      <p class="hint">
        <strong>乘算</strong>修正，用百分比表示相对基准值的变化。负数 = 减益。
      </p>
      <table v-if="mods.length" class="mods">
        <thead>
          <tr><th>属性</th><th>修正</th><th>说明</th></tr>
        </thead>
        <tbody>
          <tr v-for="m in mods" :key="m.key">
            <td>{{ m.label }}</td>
            <td :class="['val', modClass(m.percent)]">{{ pct(m.percent) }}</td>
            <td class="note">
              <template v-if="m.percent < 0">
                降低到原值的 {{ Math.round(m.value * 100) }}%
              </template>
              <template v-else>
                提升到原值的 {{ Math.round(m.value * 100) }}%
              </template>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">该状态不修改任何属性数值。</p>

      <div v-if="flags.length" class="flags">
        <span v-for="f in flags" :key="f.key" class="flag">{{ f.label }}</span>
      </div>
    </section>

    <section class="card">
      <h2>对立状态</h2>
      <p class="hint">
        同时存在时互相抵消。灰色条目属于原版状态，本 wiki 不单独收录。
      </p>
      <div v-if="(e.opposites || []).length" class="ops">
        <template v-for="op in e.opposites" :key="op">
          <a v-if="oppositeLink(op)" class="op link" :href="oppositeLink(op)">{{ op }}</a>
          <span v-else class="op">{{ op }}</span>
        </template>
      </div>
      <p v-else class="empty">没有声明对立状态。</p>
    </section>

    <section class="card">
      <h2>谁施加这个状态</h2>
      <p class="hint">
        数据包里所有会给目标挂上「{{ nameZh }}」的单位或建筑。
      </p>
      <ul v-if="appliers.length" class="appliers">
        <li v-for="a in appliers" :key="a.kind + a.id + a.field">
          <span class="kind">{{ kindLabel[a.kind] || a.kind }}</span>
          <a
            class="link"
            :href="a.kind === 'unit' ? unitUrl(a.id) : buildingUrl(a.id)"
          >{{ a.nameZh }}</a>
          <code class="field">{{ a.field }}</code>
          <span class="src">{{ a.file }}</span>
        </li>
      </ul>
      <p v-else class="empty">
        没扫到施加者 —— 可能是通过脚本或原版逻辑挂载的。
      </p>
    </section>

    <section v-if="e.uiIcon || e.effect" class="card">
      <h2>原始字段</h2>
      <dl class="raw">
        <template v-if="e.applyEffect">
          <dt>applyEffect</dt><dd><code>{{ e.applyEffect }}</code></dd>
        </template>
        <template v-if="e.effect">
          <dt>effect</dt><dd><code>{{ e.effect }}</code></dd>
        </template>
        <template v-if="e.uiIcon">
          <dt>uiIcon</dt><dd><code>{{ e.uiIcon }}</code></dd>
        </template>
      </dl>
    </section>
  </div>
</template>

<style scoped>
.effect-page { display: flex; flex-direction: column; gap: 18px; }

.eh { display: flex; align-items: center; gap: 16px; }
.eh-swatch {
  width: 46px; height: 46px; border-radius: 10px; flex: none;
  background: #444; border: 1px solid rgba(255, 255, 255, 0.18);
  box-shadow: 0 0 18px rgba(0, 0, 0, 0.35);
}
.eh-text h1 { margin: 0; font-size: 30px; line-height: 1.2; }
.eh-id { margin: 4px 0 0; opacity: 0.7; font-size: 13px; }
.eh-hidden {
  margin-left: 10px; padding: 1px 7px; border-radius: 999px;
  background: rgba(255, 160, 60, 0.16); color: #ffb454; font-size: 12px;
}

.card {
  border: 1px solid var(--vp-c-divider); border-radius: 12px;
  padding: 16px 18px; background: var(--vp-c-bg-soft);
}
.card h2 { margin: 0 0 8px; font-size: 18px; }
.hint { margin: 0 0 12px; font-size: 13px; opacity: 0.72; }
.empty { margin: 6px 0 0; font-size: 13px; opacity: 0.6; }

.mods { width: 100%; border-collapse: collapse; font-size: 14px; }
.mods th {
  text-align: left; font-weight: 600; opacity: 0.7; font-size: 13px;
  padding: 6px 10px; border-bottom: 1px solid var(--vp-c-divider);
}
.mods td { padding: 7px 10px; border-bottom: 1px solid var(--vp-c-divider); }
.mods tr:last-child td { border-bottom: none; }
.val { font-weight: 700; font-variant-numeric: tabular-nums; }
.val.down { color: #ff6b6b; }
.val.up { color: #4ade80; }
.val.flat { opacity: 0.6; }
.note { opacity: 0.65; font-size: 13px; }

.flags { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px; }
.flag {
  padding: 3px 10px; border-radius: 999px; font-size: 12px;
  background: rgba(120, 160, 255, 0.16); color: #8fb0ff;
}

.ops { display: flex; flex-wrap: wrap; gap: 8px; }
.op {
  padding: 4px 12px; border-radius: 8px; font-size: 13px;
  background: rgba(255, 255, 255, 0.06); opacity: 0.55;
}
.op.link { opacity: 1; background: rgba(120, 160, 255, 0.16); color: #8fb0ff; }
.op.link:hover { background: rgba(120, 160, 255, 0.28); }

.appliers { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.appliers li {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  font-size: 14px;
}
.kind {
  flex: none; padding: 1px 8px; border-radius: 6px; font-size: 12px;
  background: rgba(255, 255, 255, 0.08); opacity: 0.8;
}
.field { font-size: 12px; opacity: 0.7; }
.src { font-size: 12px; opacity: 0.45; margin-left: auto; }
.link { color: var(--vp-c-brand-1); text-decoration: none; }
.link:hover { text-decoration: underline; }

.raw { margin: 0; display: grid; grid-template-columns: max-content 1fr; gap: 6px 14px; font-size: 13px; }
.raw dt { opacity: 0.65; }
.raw dd { margin: 0; }
</style>
