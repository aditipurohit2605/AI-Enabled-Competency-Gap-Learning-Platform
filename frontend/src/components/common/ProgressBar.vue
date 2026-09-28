<template>
  <div class="progress-wrapper">
    <div v-if="showLabel || label" class="progress-header">
      <span v-if="label" class="progress-title">{{ label }}</span>
      <span v-if="showLabel" class="progress-pct">{{ Math.round(clampedPercentage) }}%</span>
    </div>
    <div class="progress-track" :style="{ height: height + 'px' }">
      <div
        class="progress-fill"
        :class="statusClass"
        :style="{ width: clampedPercentage + '%' }"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  percentage: {
    type: Number,
    default: 0
  },
  label: {
    type: String,
    default: ''
  },
  showLabel: {
    type: Boolean,
    default: true
  },
  height: {
    type: Number,
    default: 8
  },
  color: {
    type: String,
    default: 'auto' // 'auto' | 'primary' | 'success' | 'warning'
  }
})

const clampedPercentage = computed(() => {
  return Math.min(100, Math.max(0, props.percentage || 0))
})

const statusClass = computed(() => {
  if (props.color !== 'auto') return `color-${props.color}`
  if (clampedPercentage.value >= 80) return 'color-success'
  if (clampedPercentage.value >= 50) return 'color-accent'
  return 'color-warning'
})
</script>

<style scoped>
.progress-wrapper {
  width: 100%;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.35rem;
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.progress-title {
  color: var(--color-text-muted);
}

.progress-pct {
  color: var(--color-text-main);
}

.progress-track {
  width: 100%;
  background-color: var(--color-border);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.4s ease;
}

.color-accent {
  background-color: var(--color-accent);
}

.color-success {
  background-color: var(--color-success);
}

.color-warning {
  background-color: var(--color-warning);
}
</style>
