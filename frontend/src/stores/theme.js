import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  // Stored mode: 'light' | 'dark' | 'system'
  const savedMode = localStorage.getItem('karmayogi-theme') || 'system'
  const mode = ref(savedMode)

  // System OS preference
  const systemPrefersDark = ref(
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
      : false
  )

  // Listen to OS preference changes
  if (typeof window !== 'undefined' && window.matchMedia) {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e) => {
      systemPrefersDark.value = e.matches
      if (mode.value === 'system') {
        applyTheme(e.matches ? 'dark' : 'light')
      }
    }
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handler)
    } else if (mediaQuery.addListener) {
      mediaQuery.addListener(handler)
    }
  }

  // Resolved active theme: 'light' | 'dark'
  const currentTheme = computed(() => {
    if (mode.value === 'system') {
      return systemPrefersDark.value ? 'dark' : 'light'
    }
    return mode.value
  })

  const isDark = computed(() => currentTheme.value === 'dark')

  // Apply theme to DOM
  const applyTheme = (themeName) => {
    if (typeof document !== 'undefined') {
      const root = document.documentElement
      root.setAttribute('data-theme', themeName)
      root.style.colorScheme = themeName
    }
  }

  // Change theme mode
  const setMode = (newMode) => {
    if (!['light', 'dark', 'system'].includes(newMode)) return
    mode.value = newMode
    localStorage.setItem('karmayogi-theme', newMode)
    applyTheme(currentTheme.value)
  }

  // Quick cycle: light -> dark -> system -> light
  const toggleTheme = () => {
    if (mode.value === 'light') {
      setMode('dark')
    } else if (mode.value === 'dark') {
      setMode('system')
    } else {
      setMode('light')
    }
  }

  // Initialize on store creation
  applyTheme(currentTheme.value)

  return {
    mode,
    currentTheme,
    isDark,
    setMode,
    toggleTheme
  }
})
