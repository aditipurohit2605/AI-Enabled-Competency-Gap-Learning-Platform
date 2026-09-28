<template>
  <div class="theme-toggle-wrapper">
    <button
      class="theme-toggle-btn"
      :title="`Theme: ${currentLabel} (Click to switch)`"
      :aria-label="`Switch color theme. Current theme is ${currentLabel}`"
      @click="themeStore.toggleTheme()"
    >
      <span class="theme-icon" aria-hidden="true">
        <!-- Sun icon for Light -->
        <svg
          v-if="themeStore.mode === 'light'"
          class="icon-svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>

        <!-- Moon icon for Dark -->
        <svg
          v-else-if="themeStore.mode === 'dark'"
          class="icon-svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>

        <!-- Monitor icon for System -->
        <svg
          v-else
          class="icon-svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
          <line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" />
        </svg>
      </span>
      <span class="theme-text">{{ currentLabel }}</span>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

const currentLabel = computed(() => {
  if (themeStore.mode === 'light') return 'Light'
  if (themeStore.mode === 'dark') return 'Dark'
  return `Auto (${themeStore.currentTheme})`
})
</script>

<style scoped>
.theme-toggle-wrapper {
  display: inline-flex;
  align-items: center;
}

.theme-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.35rem 0.65rem;
  font-family: var(--font-family);
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-main);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  user-select: none;
}

.theme-toggle-btn:hover {
  background-color: var(--color-surface-hover);
  border-color: var(--color-border-subtle);
  color: var(--color-accent);
}

.theme-toggle-btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.icon-svg {
  width: 14px;
  height: 14px;
  display: block;
}

.theme-text {
  text-transform: capitalize;
}
</style>
