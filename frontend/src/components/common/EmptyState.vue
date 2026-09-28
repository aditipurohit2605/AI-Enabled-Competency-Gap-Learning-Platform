<template>
  <div class="empty-state">
    <div class="empty-icon">{{ icon }}</div>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-description">{{ description }}</p>
    <div v-if="$slots.action" class="empty-action">
      <slot name="action"></slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  icon: {
    type: String,
    default: '📭'
  },
  title: {
    type: String,
    default: 'No items to display'
  },
  description: {
    type: String,
    default: 'There is no data available for this section yet.'
  }
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 3.5rem 1.5rem;
  background-color: var(--color-surface);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text-main);
  margin-bottom: 0.5rem;
}

.empty-description {
  max-width: 420px;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: 1.5rem;
}

.empty-action {
  display: flex;
  gap: 0.75rem;
}
</style>
