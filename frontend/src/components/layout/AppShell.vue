<template>
  <div class="app-layout">
    <!-- Top Navigation Bar -->
    <header class="app-header">
      <div class="header-brand">
        <div class="brand-logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div>
          <span class="brand-title">Karmayogi Competency</span>
          <span class="brand-subtitle">Ministry of Statistics & Programme Implementation</span>
        </div>
      </div>

      <div class="header-user" v-if="auth.isAuthenticated">
        <div class="user-meta">
          <span class="user-name">{{ auth.userName }}</span>
          <span class="user-role badge" :class="roleBadgeClass">{{ auth.role }}</span>
        </div>
        <button class="btn btn-secondary btn-sm" @click="handleLogout">
          Sign Out
        </button>
      </div>
    </header>

    <div class="app-body">
      <!-- Sidebar Navigation -->
      <aside class="app-sidebar">
        <nav class="sidebar-nav">
          <div class="nav-section-title">Learner Portal</div>
          <router-link to="/dashboard" class="nav-item" active-class="active">
            <span class="nav-icon">📊</span>
            <span>Dashboard</span>
          </router-link>
          <router-link to="/profile" class="nav-item" active-class="active">
            <span class="nav-icon">👤</span>
            <span>My Profile & Skills</span>
          </router-link>
          <router-link to="/gap" class="nav-item" active-class="active">
            <span class="nav-icon">🎯</span>
            <span>Gap Report</span>
          </router-link>
          <router-link to="/path" class="nav-item" active-class="active">
            <span class="nav-icon">🗺️</span>
            <span>Learning Path</span>
          </router-link>
          <router-link to="/quiz" class="nav-item" active-class="active">
            <span class="nav-icon">✍️</span>
            <span>Assessments</span>
          </router-link>
          <router-link to="/history" class="nav-item" active-class="active">
            <span class="nav-icon">📈</span>
            <span>History & Trend</span>
          </router-link>

          <!-- Trainer Portal (Trainer & Admin) -->
          <template v-if="auth.isTrainer || auth.isAdmin">
            <div class="nav-section-title" style="margin-top: 1.5rem;">Trainer Portal</div>
            <router-link to="/trainer/documents" class="nav-item" active-class="active">
              <span class="nav-icon">📚</span>
              <span>Documents & MCQs</span>
            </router-link>
            <router-link to="/trainer/review" class="nav-item" active-class="active">
              <span class="nav-icon">📝</span>
              <span>Review Questions</span>
            </router-link>
          </template>

          <!-- Admin Portal (Admin Only) -->
          <template v-if="auth.isAdmin">
            <div class="nav-section-title" style="margin-top: 1.5rem;">Admin Portal</div>
            <router-link to="/admin/analytics" class="nav-item" active-class="active">
              <span class="nav-icon">📊</span>
              <span>Analytics & Heatmap</span>
            </router-link>
            <router-link to="/admin/framework" class="nav-item" active-class="active">
              <span class="nav-icon">🏛️</span>
              <span>Framework Manager</span>
            </router-link>
            <router-link to="/admin/users" class="nav-item" active-class="active">
              <span class="nav-icon">👥</span>
              <span>User Directory</span>
            </router-link>
          </template>
        </nav>
      </aside>

      <!-- Main Content Stage -->
      <main class="app-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const roleBadgeClass = computed(() => {
  if (auth.isAdmin) return 'badge-danger'
  if (auth.isTrainer) return 'badge-warning'
  return 'badge-info'
})

const handleLogout = () => {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  height: 64px;
  background-color: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  position: sticky;
  top: 0;
  z-index: 50;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.brand-logo {
  color: var(--color-accent);
  display: flex;
  align-items: center;
}

.brand-title {
  font-size: var(--font-size-base);
  font-weight: 800;
  color: var(--color-text-main);
  display: block;
  line-height: 1.2;
}

.brand-subtitle {
  font-size: 0.6875rem;
  color: var(--color-text-muted);
  display: block;
}

.header-user {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.user-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.user-name {
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.user-role {
  text-transform: capitalize;
}

.app-body {
  flex: 1;
  display: flex;
}

.app-sidebar {
  width: 250px;
  background-color: var(--color-surface);
  border-right: 1px solid var(--color-border);
  padding: 1.5rem 1rem;
  flex-shrink: 0;
}

.nav-section-title {
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
  color: var(--color-text-light);
  margin-bottom: 0.75rem;
  padding-left: 0.75rem;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-muted);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.nav-item:hover:not(.disabled) {
  background-color: var(--color-surface-hover);
  color: var(--color-text-main);
}

.nav-item.active {
  background-color: var(--color-accent-light);
  color: var(--color-accent);
  font-weight: 600;
}

.nav-item.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.nav-icon {
  font-size: 1.1rem;
}

.app-content {
  flex: 1;
  padding: 2rem;
  background-color: var(--color-bg);
  overflow-y: auto;
  max-width: 1300px;
}

@media (max-width: 800px) {
  .app-sidebar {
    width: 70px;
    padding: 1rem 0.5rem;
  }
  .nav-item span:not(.nav-icon) {
    display: none;
  }
  .nav-section-title {
    display: none;
  }
  .brand-subtitle {
    display: none;
  }
}
</style>
