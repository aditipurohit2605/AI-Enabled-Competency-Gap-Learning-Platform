<template>
  <span class="level-badge" :class="`level-${validLevel}`" :title="`Level ${validLevel}: ${levelName}`">
    <span class="level-number">L{{ validLevel }}</span>
    <span v-if="showName" class="level-text">{{ levelName }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  level: {
    type: [Number, String],
    default: 1
  },
  showName: {
    type: Boolean,
    default: false
  }
})

const LEVEL_NAMES = {
  1: 'Novice',
  2: 'Beginner',
  3: 'Intermediate',
  4: 'Advanced',
  5: 'Expert'
}

const validLevel = computed(() => {
  const num = Math.round(Number(props.level) || 1)
  return Math.min(5, Math.max(1, num))
})

const levelName = computed(() => LEVEL_NAMES[validLevel.value] || 'Novice')
</script>

<style scoped>
.level-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.5rem;
  font-size: var(--font-size-xs);
  font-weight: 700;
  border-radius: var(--radius-sm);
  white-space: nowrap;
}

.level-number {
  font-weight: 800;
  letter-spacing: 0.02em;
}

.level-text {
  font-weight: 500;
  font-size: 0.7rem;
  opacity: 0.9;
}
</style>
