<script setup>
import { computed } from 'vue'
import { starLabel } from '../composables/useRemoteData'

const props = defineProps({
  building: { type: Object, required: true }
})

const b = computed(() => props.building || {})
const id = computed(() => b.value.id || '')
const link = computed(() => `/buildings/${id.value}`)
const nameZh = computed(() => b.value.nameZh || id.value)
const showEn = computed(() => !!b.value.nameZh && b.value.nameZh !== id.value)
const packs = computed(() => (Array.isArray(b.value.packs) ? b.value.packs : []))
</script>

<template>
  <a class="building-card" :href="link">
    <div class="bc-head">
      <span class="bc-zh">{{ nameZh }}</span>
      <span v-if="showEn" class="bc-en mz-mono">{{ id }}</span>
    </div>

    <div class="bc-badges">
      <span :class="['mz-badge', 'star-' + (b.star || '')]">
        {{ b.star || '?' }} · {{ starLabel(b.star) }}
      </span>
      <span v-if="b.author" class="mz-badge author">{{ b.author }}</span>
      <span v-if="b.category" class="mz-badge">{{ b.category }}</span>
    </div>

    <div v-if="packs.length" class="bc-packs">
      <span v-for="p in packs" :key="p" class="bc-pack">{{ p }}</span>
    </div>
  </a>
</template>

<style scoped>
.building-card {
  display: block;
  padding: 0.85rem 0.95rem;
  border-radius: 12px;
  border: 1px solid var(--mz-border);
  background: linear-gradient(155deg, var(--mz-surface-2), var(--mz-surface));
  text-decoration: none !important;
  color: inherit;
  transition: transform 0.14s ease, border-color 0.14s ease, box-shadow 0.14s ease;
}

.building-card:hover {
  transform: translateY(-2px);
  border-color: var(--mz-border-strong);
  box-shadow: var(--mz-glow);
}

.bc-head {
  display: flex;
  align-items: baseline;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.bc-zh {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--vp-c-text-1);
}

.bc-en {
  font-size: 0.76rem;
  color: var(--vp-c-text-3);
}

.bc-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin: 0.55rem 0 0;
}

.bc-packs {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  margin-top: 0.6rem;
  padding-top: 0.55rem;
  border-top: 1px solid var(--mz-border);
}

.bc-pack {
  font-size: 0.72rem;
  color: var(--vp-c-text-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>