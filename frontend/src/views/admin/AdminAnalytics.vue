<template>
  <div class="admin-analytics">
    <div class="page-header">
      <div>
        <h1 class="page-title">Executive Analytics & Heatmap</h1>
        <p class="page-description">
          Cross-organizational competency metrics, readiness benchmarks, and learner proficiency distribution across the Karmayogi framework.
        </p>
      </div>

      <div class="role-filter" v-if="roles.length > 0">
        <label for="role-select" class="filter-label">Filter by Target Role:</label>
        <select
          id="role-select"
          v-model="selectedRoleId"
          class="form-control role-dropdown"
          @change="loadAnalytics"
        >
          <option v-for="r in roles" :key="r.id" :value="r.id">
            {{ r.name }}
          </option>
        </select>
      </div>
    </div>

    <LoadingState v-if="isLoading" message="Aggregating organizational competency data..." />
    <ErrorState v-else-if="fetchError" :message="fetchError" :retry="loadAnalytics" />

    <div v-else-if="analytics" class="analytics-content">
      <!-- KPI Overview Cards -->
      <div class="kpi-grid">
        <div class="card kpi-card">
          <span class="kpi-icon">👥</span>
          <div class="kpi-info">
            <span class="kpi-label">Active Learners</span>
            <span class="kpi-value">{{ analytics.num_learners }}</span>
          </div>
          <span class="kpi-caption">Registered ministry personnel</span>
        </div>

        <div class="card kpi-card">
          <span class="kpi-icon">🎯</span>
          <div class="kpi-info">
            <span class="kpi-label">Average Readiness</span>
            <span class="kpi-value">{{ analytics.average_readiness }}%</span>
          </div>
          <div class="kpi-bar">
            <ProgressBar :percentage="analytics.average_readiness" :height="8" :show-label="false" />
          </div>
          <span class="kpi-caption">For role: {{ analytics.role_name || 'All Roles' }}</span>
        </div>

        <div class="card kpi-card">
          <span class="kpi-icon">✍️</span>
          <div class="kpi-info">
            <span class="kpi-label">Quizzes Completed</span>
            <span class="kpi-value">{{ analytics.total_quizzes_taken }}</span>
          </div>
          <span class="kpi-caption">Diagnostic & mastery attempts</span>
        </div>
      </div>

      <!-- Top 5 Gaps Section -->
      <div class="card chart-card">
        <div class="card-header">
          <div>
            <h3 class="card-title">Top 5 Most Common Competency Gaps</h3>
            <p class="card-subtitle">
              Prioritized by number of affected learners and average level deficit for {{ analytics.role_name }}.
            </p>
          </div>
        </div>

        <div v-if="analytics.top_gaps && analytics.top_gaps.length > 0" class="gaps-container">
          <div class="chart-wrapper">
            <Bar :key="themeStore.currentTheme" :data="topGapsChartData" :options="topGapsChartOptions" />
          </div>

          <div class="gaps-summary-list">
            <div v-for="gap in analytics.top_gaps" :key="gap.competency_id" class="gap-item-card">
              <div class="gap-item-header">
                <strong>{{ gap.competency_name }}</strong>
                <span class="badge badge-warning">Avg Gap: -{{ gap.average_gap }}</span>
              </div>
              <div class="gap-item-stat">
                <span>Affected Personnel:</span>
                <strong>{{ gap.learners_affected }} / {{ analytics.num_learners }}</strong>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="text-center py-8 text-muted">
          <p>No competency gaps detected for the selected role! All assessed learners meet role requirements.</p>
        </div>
      </div>

      <!-- Competency-by-Learner Heatmap -->
      <div class="card heatmap-card">
        <div class="card-header heatmap-header">
          <div>
            <h3 class="card-title">Learner Competency Heatmap Matrix</h3>
            <p class="card-subtitle">
              Matrix of active learners and their current evaluated proficiency levels (0 to 5) across competencies.
            </p>
          </div>

          <!-- Heatmap Color Legend -->
          <div class="heatmap-legend">
            <span class="legend-title">Proficiency:</span>
            <div class="legend-items">
              <span class="legend-chip level-0">L0 (Unassessed)</span>
              <span class="legend-chip level-1">L1 (Beginner)</span>
              <span class="legend-chip level-2">L2 (Foundational)</span>
              <span class="legend-chip level-3">L3 (Proficient)</span>
              <span class="legend-chip level-4">L4 (Advanced)</span>
              <span class="legend-chip level-5">L5 (Expert)</span>
            </div>
          </div>
        </div>

        <div v-if="analytics.learner_matrix && analytics.learner_matrix.length > 0" class="table-container heatmap-table-wrap">
          <table class="table heatmap-table">
            <thead>
              <tr>
                <th class="sticky-col learner-col">Learner</th>
                <th
                  v-for="c in analytics.competency_headers"
                  :key="c.id"
                  class="comp-col-header"
                  :title="c.name"
                >
                  {{ c.name }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="learner in analytics.learner_matrix" :key="learner.learner_id">
                <td class="sticky-col learner-cell">
                  <div class="learner-name">{{ learner.learner_name }}</div>
                  <div class="learner-email">{{ learner.learner_email }}</div>
                </td>
                <td
                  v-for="c in analytics.competency_headers"
                  :key="c.id"
                  class="heatmap-cell"
                  :class="'heat-level-' + Math.floor(learner.competencies[String(c.id)] || 0)"
                  :title="`${learner.learner_name} · ${c.name}: Level ${learner.competencies[String(c.id)] || 0}`"
                >
                  <span class="heat-val">
                    L{{ Math.floor(learner.competencies[String(c.id)] || 0) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="text-center py-6 text-muted">
          No learners registered yet.
        </div>
      </div>

      <!-- Quiz Completion & Average Score per Competency -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Assessment Activity & Average Score by Competency</h3>
        </div>

        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Competency Name</th>
                <th>Assessments Completed</th>
                <th>Average Score</th>
                <th>Score Indicator</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="stat in analytics.quiz_stats_by_competency" :key="stat.competency_id">
                <td><strong>{{ stat.competency_name }}</strong></td>
                <td>{{ stat.quiz_count }}</td>
                <td>
                  <span v-if="stat.quiz_count > 0" class="score-badge" :class="getScoreClass(stat.average_score)">
                    {{ stat.average_score }}%
                  </span>
                  <span v-else class="text-muted">No attempts</span>
                </td>
                <td style="width: 250px;">
                  <ProgressBar
                    v-if="stat.quiz_count > 0"
                    :percentage="stat.average_score"
                    :height="8"
                    :show-label="false"
                  />
                  <span v-else class="text-muted text-xs">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale
} from 'chart.js'
import { Bar } from 'vue-chartjs'
import api from '@/api'
import { useThemeStore } from '@/stores/theme'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import ProgressBar from '@/components/common/ProgressBar.vue'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const themeStore = useThemeStore()
const roles = ref([])
const selectedRoleId = ref(null)
const analytics = ref(null)
const isLoading = ref(true)
const fetchError = ref(null)

const loadRoles = async () => {
  try {
    const res = await api.get('/roles')
    roles.value = res.roles || []
    if (roles.value.length > 0 && !selectedRoleId.value) {
      selectedRoleId.value = roles.value[0].id
    }
  } catch (err) {
    console.error('Failed to load roles', err)
  }
}

const loadAnalytics = async () => {
  isLoading.value = true
  fetchError.value = null
  try {
    const params = {}
    if (selectedRoleId.value) params.role_id = selectedRoleId.value
    const res = await api.get('/admin/analytics', { params })
    analytics.value = res
  } catch (err) {
    fetchError.value = err.message || 'Failed to load executive analytics'
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  await loadRoles()
  await loadAnalytics()
})

const getScoreClass = (score) => {
  if (score >= 80) return 'text-success'
  if (score >= 60) return 'text-warning'
  return 'text-danger'
}

// Chart.js data for Top 5 Gaps
const topGapsChartData = computed(() => {
  if (!analytics.value?.top_gaps) return { labels: [], datasets: [] }
  const gaps = analytics.value.top_gaps
  const isDark = themeStore.isDark

  return {
    labels: gaps.map((g) => g.competency_name),
    datasets: [
      {
        label: 'Average Competency Deficit (Levels)',
        backgroundColor: isDark ? '#f87171' : '#ef4444',
        borderRadius: 6,
        data: gaps.map((g) => g.average_gap)
      },
      {
        label: 'Affected Personnel',
        backgroundColor: isDark ? '#fbbf24' : '#f59e0b',
        borderRadius: 6,
        data: gaps.map((g) => g.learners_affected)
      }
    ]
  }
})

const topGapsChartOptions = computed(() => {
  const isDark = themeStore.isDark
  const textMuted = isDark ? '#94a3b8' : '#64748b'
  const textMain = isDark ? '#f1f5f9' : '#0f172a'
  const gridLine = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.05)'

  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: textMain,
          font: { family: 'inherit', size: 12, weight: '600' }
        }
      },
      tooltip: {
        backgroundColor: isDark ? '#1e293b' : '#0f172a',
        titleColor: '#ffffff',
        bodyColor: '#ffffff',
        borderColor: isDark ? '#334155' : '#e2e8f0',
        borderWidth: 1,
        padding: 10,
        cornerRadius: 6
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { color: textMuted },
        grid: { color: gridLine }
      },
      x: {
        ticks: { color: textMuted },
        grid: { display: false }
      }
    }
  }
})
</script>

<style scoped>
.admin-analytics {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.5rem;
  flex-wrap: wrap;
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

.role-filter {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: var(--color-surface);
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.filter-label {
  font-size: var(--font-size-xs);
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-text-light);
  white-space: nowrap;
}

.role-dropdown {
  min-width: 200px;
}

.analytics-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* KPI Cards */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.25rem;
}

.kpi-card {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  position: relative;
}

.kpi-icon {
  font-size: 1.5rem;
}

.kpi-info {
  display: flex;
  flex-direction: column;
}

.kpi-label {
  font-size: var(--font-size-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-light);
}

.kpi-value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text-main);
  line-height: 1.2;
}

.kpi-caption {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: auto;
}

.kpi-bar {
  margin: 0.25rem 0;
}

/* Gaps Chart & List */
.gaps-container {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
  align-items: center;
}

.chart-wrapper {
  height: 280px;
  position: relative;
}

.gaps-summary-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.gap-item-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.gap-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-sm);
}

.gap-item-stat {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

/* Heatmap */
.heatmap-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 1rem;
}

.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.legend-title {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-muted);
}

.legend-items {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.legend-chip {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
}

.level-0, .heat-level-0 { background-color: #f1f5f9; color: #475569; }
.level-1, .heat-level-1 { background-color: #fee2e2; color: #991b1b; }
.level-2, .heat-level-2 { background-color: #ffedd5; color: #9a3412; }
.level-3, .heat-level-3 { background-color: #fef9c3; color: #854d0e; }
.level-4, .heat-level-4 { background-color: #e0f2fe; color: #0369a1; }
.level-5, .heat-level-5 { background-color: #dcfce7; color: #166534; }

[data-theme="dark"] .level-0, [data-theme="dark"] .heat-level-0 { background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; }
[data-theme="dark"] .level-1, [data-theme="dark"] .heat-level-1 { background-color: rgba(239, 68, 68, 0.25); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }
[data-theme="dark"] .level-2, [data-theme="dark"] .heat-level-2 { background-color: rgba(249, 115, 22, 0.25); color: #fdba74; border: 1px solid rgba(249, 115, 22, 0.4); }
[data-theme="dark"] .level-3, [data-theme="dark"] .heat-level-3 { background-color: rgba(234, 179, 8, 0.25); color: #fde047; border: 1px solid rgba(234, 179, 8, 0.4); }
[data-theme="dark"] .level-4, [data-theme="dark"] .heat-level-4 { background-color: rgba(14, 165, 233, 0.25); color: #7dd3fc; border: 1px solid rgba(14, 165, 233, 0.4); }
[data-theme="dark"] .level-5, [data-theme="dark"] .heat-level-5 { background-color: rgba(34, 197, 94, 0.25); color: #86efac; border: 1px solid rgba(34, 197, 94, 0.4); }

.score-badge {
  font-weight: 700;
}

@media (max-width: 900px) {
  .gaps-container {
    grid-template-columns: 1fr;
  }
}
</style>
