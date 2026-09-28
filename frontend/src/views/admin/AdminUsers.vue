<template>
  <div class="admin-users">
    <div class="page-header">
      <div>
        <h1 class="page-title">User Directory</h1>
        <p class="page-description">
          Overview of registered system users, roles, and administrative privileges.
        </p>
      </div>

      <div class="user-stats-summary">
        <span class="stat-pill">Total: <strong>{{ users.length }}</strong></span>
        <span class="stat-pill pill-learner">Learners: <strong>{{ learnerCount }}</strong></span>
        <span class="stat-pill pill-trainer">Trainers: <strong>{{ trainerCount }}</strong></span>
        <span class="stat-pill pill-admin">Admins: <strong>{{ adminCount }}</strong></span>
      </div>
    </div>

    <!-- Filters toolbar -->
    <div class="filters-bar">
      <div class="search-input-wrap">
        <span class="search-icon">🔍</span>
        <input
          v-model="searchQuery"
          type="text"
          class="form-control search-input"
          placeholder="Search by user name or email..."
        />
      </div>

      <div class="role-filter-tabs">
        <button
          class="filter-tab"
          :class="{ active: roleFilter === 'all' }"
          @click="roleFilter = 'all'"
        >
          All
        </button>
        <button
          class="filter-tab"
          :class="{ active: roleFilter === 'learner' }"
          @click="roleFilter = 'learner'"
        >
          Learners
        </button>
        <button
          class="filter-tab"
          :class="{ active: roleFilter === 'trainer' }"
          @click="roleFilter = 'trainer'"
        >
          Trainers
        </button>
        <button
          class="filter-tab"
          :class="{ active: roleFilter === 'admin' }"
          @click="roleFilter = 'admin'"
        >
          Admins
        </button>
      </div>
    </div>

    <LoadingState v-if="isLoading" message="Loading user directory..." />
    <ErrorState v-else-if="fetchError" :message="fetchError" :retry="loadUsers" />

    <div v-else class="card table-card">
      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 70px;">ID</th>
              <th>Full Name</th>
              <th>Email Address</th>
              <th style="width: 130px;">Assigned Role</th>
              <th style="width: 180px;">Member Since</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="filteredUsers.length === 0">
              <td colspan="5" class="text-center text-muted py-6">
                No users match the search criteria.
              </td>
            </tr>
            <tr v-for="u in filteredUsers" :key="u.id">
              <td class="text-muted">#{{ u.id }}</td>
              <td>
                <div class="user-cell">
                  <div class="user-avatar">{{ getInitials(u.name) }}</div>
                  <strong>{{ u.name }}</strong>
                </div>
              </td>
              <td>{{ u.email }}</td>
              <td>
                <span class="badge" :class="getRoleBadgeClass(u.role)">
                  {{ u.role.toUpperCase() }}
                </span>
              </td>
              <td class="text-muted text-sm">{{ formatDate(u.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'

const users = ref([])
const isLoading = ref(true)
const fetchError = ref(null)

const searchQuery = ref('')
const roleFilter = ref('all')

const loadUsers = async () => {
  isLoading.value = true
  fetchError.value = null
  try {
    const res = await api.get('/admin/users')
    users.value = res.users || []
  } catch (err) {
    fetchError.value = err.message || 'Failed to load user directory'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadUsers()
})

const learnerCount = computed(() => users.value.filter((u) => u.role === 'learner').length)
const trainerCount = computed(() => users.value.filter((u) => u.role === 'trainer').length)
const adminCount = computed(() => users.value.filter((u) => u.role === 'admin').length)

const filteredUsers = computed(() => {
  return users.value.filter((u) => {
    if (roleFilter.value !== 'all' && u.role !== roleFilter.value) {
      return false
    }
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase()
      const matchName = u.name && u.name.toLowerCase().includes(q)
      const matchEmail = u.email && u.email.toLowerCase().includes(q)
      return matchName || matchEmail
    }
    return true
  })
})

const getRoleBadgeClass = (role) => {
  if (role === 'admin') return 'badge-danger'
  if (role === 'trainer') return 'badge-warning'
  return 'badge-info'
}

const getInitials = (name) => {
  if (!name) return 'U'
  const parts = name.trim().split(' ')
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
}

const formatDate = (isoStr) => {
  if (!isoStr) return '—'
  const d = new Date(isoStr)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>

<style scoped>
.admin-users {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 1rem;
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 800;
  color: var(--color-text-main);
  margin-bottom: 0.25rem;
}

.page-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  max-width: 650px;
}

.user-stats-summary {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.stat-pill {
  font-size: var(--font-size-xs);
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
}

.pill-learner strong { color: #2563eb; }
.pill-trainer strong { color: #d97706; }
.pill-admin strong { color: #dc2626; }

.filters-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.search-input-wrap {
  position: relative;
  flex: 1;
  max-width: 400px;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.875rem;
  color: var(--color-text-light);
}

.search-input {
  padding-left: 2.25rem;
}

.role-filter-tabs {
  display: flex;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  padding: 0.25rem;
  border-radius: var(--radius-md);
  gap: 0.25rem;
}

.filter-tab {
  background: none;
  border: none;
  padding: 0.375rem 0.875rem;
  font-size: var(--font-size-xs);
  font-weight: 600;
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.filter-tab:hover {
  color: var(--color-text-main);
}

.filter-tab.active {
  background-color: var(--color-accent);
  color: white;
}

.table-card {
  padding: 0;
  overflow: hidden;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-accent-light);
  color: var(--color-accent);
  font-size: 0.75rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
