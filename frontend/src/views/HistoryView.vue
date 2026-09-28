<template>
  <div class="history-page">
    <div class="page-header">
      <div>
        <h1>Assessment History & Readiness Trend</h1>
        <p>Track your evaluation scores and observe role readiness progression across time.</p>
      </div>

      <div class="role-selector" v-if="roles.length">
        <label for="trend-role-select" class="form-label" style="margin-bottom: 0;">Target Role:</label>
        <select
          id="trend-role-select"
          v-model="selectedRoleId"
          @change="loadTrendData"
          class="form-control select-role"
        >
          <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
      </div>
    </div>

    <!-- Section 1: Readiness Trend Line Chart -->
    <div class="card trend-card">
      <div class="card-header">
        <h3 class="card-title">Role Readiness Trajectory (%)</h3>
        <span class="text-sm text-muted">Progression across diagnostic and quiz submissions</span>
      </div>

      <LoadingState v-if="isLoadingTrend" message="Plotting historical readiness..." />
      <ErrorState v-else-if="trendError" :message="trendError" @retry="loadTrendData" />
      <EmptyState
        v-else-if="snapshots.length === 0"
        icon="📉"
        title="No trend points recorded"
        description="Submit a quiz or diagnostic evaluation to start tracking your readiness over time."
      />
      <div v-else class="chart-wrapper">
        <Line :key="themeStore.currentTheme" :data="lineChartData" :options="lineChartOptions" />
      </div>
    </div>

    <!-- Section 2: Completed Quiz Sessions History -->
    <div class="card history-card">
      <div class="card-header">
        <h3 class="card-title">Completed Assessment Sessions</h3>
        <span class="text-sm text-muted">Newest assessments first</span>
      </div>

      <LoadingState v-if="isLoadingHistory" message="Loading past sessions..." />
      <ErrorState v-else-if="historyError" :message="historyError" @retry="loadHistoryData" />
      <EmptyState
        v-else-if="sessions.length === 0"
        icon="📋"
        title="No past assessment sessions"
        description="You have not completed any quizzes yet."
      >
        <template #action>
          <router-link to="/quiz" class="btn btn-primary btn-sm">Take a Quiz</router-link>
        </template>
      </EmptyState>

      <div v-else class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Competency</th>
              <th>Items</th>
              <th>Score</th>
              <th>Proficiency Change</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sess in sessions" :key="sess.id">
              <td>{{ formatDate(sess.submitted_at) }}</td>
              <td><strong>{{ sess.competency_name || 'General' }}</strong></td>
              <td>{{ sess.question_count }} questions</td>
              <td>
                <span class="badge" :class="getScoreBadge(sess.score_pct)">
                  {{ Math.round(sess.score_pct || 0) }}%
                </span>
              </td>
              <td>
                <div class="level-diff">
                  <LevelBadge :level="sess.level_before || 1" />
                  <span class="arrow">&rarr;</span>
                  <LevelBadge :level="sess.level_after || 1" :showName="true" />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
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
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Filler
} from 'chart.js'
import { Line } from 'vue-chartjs'
import api from '@/api'
import { useThemeStore } from '@/stores/theme'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LevelBadge from '@/components/common/LevelBadge.vue'

ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale, Filler)

const themeStore = useThemeStore()
const roles = ref([])
const selectedRoleId = ref(null)

const snapshots = ref([])
const isLoadingTrend = ref(false)
const trendError = ref('')

const sessions = ref([])
const isLoadingHistory = ref(false)
const historyError = ref('')

const formatDate = (isoStr) => {
  if (!isoStr) return 'N/A'
  const d = new Date(isoStr)
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getScoreBadge = (score) => {
  if (score >= 80) return 'badge-success'
  if (score >= 60) return 'badge-info'
  return 'badge-warning'
}

const lineChartData = computed(() => {
  const points = snapshots.value || []
  const isDark = themeStore.isDark

  return {
    labels: points.map((p) => {
      const d = new Date(p.taken_at)
      return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
    }),
    datasets: [
      {
        label: 'Role Readiness Percentage (%)',
        backgroundColor: isDark ? 'rgba(59, 130, 246, 0.2)' : 'rgba(37, 99, 235, 0.1)',
        borderColor: isDark ? '#60a5fa' : '#2563eb',
        pointBackgroundColor: isDark ? '#3b82f6' : '#2563eb',
        pointBorderColor: isDark ? '#ffffff' : '#1e3a8a',
        pointRadius: 5,
        pointHoverRadius: 7,
        tension: 0.3,
        fill: true,
        data: points.map((p) => Math.round(p.readiness_pct))
      }
    ]
  }
})

const lineChartOptions = computed(() => {
  const isDark = themeStore.isDark
  const textMuted = isDark ? '#94a3b8' : '#64748b'
  const textMain = isDark ? '#f1f5f9' : '#0f172a'
  const gridLine = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)'

  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: textMain,
          font: { family: 'Inter', size: 12 }
        }
      },
      tooltip: {
        backgroundColor: isDark ? '#1e293b' : '#0f172a',
        titleColor: '#ffffff',
        bodyColor: '#ffffff',
        borderColor: isDark ? '#334155' : '#e2e8f0',
        borderWidth: 1
      }
    },
    scales: {
      y: {
        min: 0,
        max: 100,
        ticks: {
          callback: (v) => `${v}%`,
          stepSize: 20,
          color: textMuted,
          font: { family: 'Inter' }
        },
        grid: {
          color: gridLine
        },
        title: {
          display: true,
          text: 'Readiness %',
          color: textMuted
        }
      },
      x: {
        ticks: {
          color: textMuted,
          font: { family: 'Inter', size: 11 }
        },
        grid: {
          color: gridLine
        }
      }
    }
  }
})

const loadTrendData = async () => {
  if (!selectedRoleId.value) return
  isLoadingTrend.value = true
  trendError.value = ''
  try {
    const res = await api.get(`/progress/gap-trend?role_id=${selectedRoleId.value}`)
    snapshots.value = res.snapshots || []
  } catch (err) {
    trendError.value = err.message || 'Failed to load readiness trend'
  } finally {
    isLoadingTrend.value = false
  }
}

const loadHistoryData = async () => {
  isLoadingHistory.value = true
  historyError.value = ''
  try {
    const res = await api.get('/quiz/history')
    sessions.value = res.history || []
  } catch (err) {
    historyError.value = err.message || 'Failed to load quiz history'
  } finally {
    isLoadingHistory.value = false
  }
}

onMounted(async () => {
  try {
    const roleRes = await api.get('/roles')
    roles.value = roleRes.roles || []
    if (roles.value.length > 0) {
      selectedRoleId.value = roles.value[0].id
    }
  } catch {
    // Continue
  }
  loadTrendData()
  loadHistoryData()
})
</script>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.role-selector {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.select-role {
  width: 250px;
}

.chart-wrapper {
  position: relative;
  height: 280px;
  width: 100%;
}

.level-diff {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.arrow {
  color: var(--color-text-muted);
}
</style>
