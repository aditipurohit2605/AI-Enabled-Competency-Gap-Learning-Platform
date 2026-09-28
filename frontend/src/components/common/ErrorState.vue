<template>
  <div class="error-state">
    <div class="error-icon">⚠️</div>
    <div class="error-content">
      <h4 class="error-title">{{ title }}</h4>
      <p class="error-message">{{ message }}</p>
    </div>
    <button v-if="retryable" class="btn btn-secondary btn-sm" @click="$emit('retry')">
      Try Again
    </button>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: 'Something went wrong'
  },
  message: {
    type: String,
    default: 'Failed to load content. Please check your network or try again.'
  },
  retryable: {
    type: Boolean,
    default: true
  }
})

defineEmits(['retry'])
</script>

<style scoped>
.error-state {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  background-color: var(--color-danger-light);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-lg);
  margin: 1rem 0;
}

.error-icon {
  font-size: 1.75rem;
  flex-shrink: 0;
}

.error-content {
  flex: 1;
}

.error-title {
  color: var(--color-danger-text);
  font-size: var(--font-size-base);
  margin-bottom: 0.25rem;
}

.error-message {
  color: var(--color-danger-text);
  opacity: 0.9;
  font-size: var(--font-size-sm);
}
</style>
