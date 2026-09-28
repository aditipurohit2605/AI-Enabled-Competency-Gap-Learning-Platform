<template>
  <div class="gap-page">
    <div class="page-header">
      <div>
        <h1>Role Gap Analysis</h1>
        <p>Compare your current assessed skills against official role requirements and identify prerequisite bottlenecks.</p>
      </div>

      <div class="role-selector" v-if="roles.length">
        <label for="gap-role-select" class="form-label" style="margin-bottom: 0;">Target Role:</label>
        <select
          id="gap-role-select"
          v-model="selectedRoleId"
          @change="loadGapReport"
          class="form-control select-role"
        >
          <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
      </div>
    </div>

    <LoadingState v-if="isLoading" message="Calculating role gaps and prerequisite dependencies..." />
    <ErrorState v-else-if="errorMessage" :message="errorMessage" @retry="loadGapReport" />

    <div v-else-if="gapData" class="gap-content">
      <!-- Readiness Overview Card -->
      <div class="card readiness-card">
        <div class="readiness-header">
          <div>
            <h3>Overall Role Readiness</h3>
            <p>Target Role: <strong>{{ gapData.role?.name }}</strong></p>
          </div>
          <div class="readiness-score">{{ Math.round(gapData.readiness_percentage) }}%</div>
        </div>
        <ProgressBar :percentage="gapData.readiness_percentage" :height="12" />
      </div>

      <!-- Chart: Required vs Current -->
      <div class="card chart-card">
        <div class="card-header">
          <h3 class="card-title">Competency Comparison: Current vs. Required Level</h3>
          <span class="text-sm text-muted">Levels 1 to 5 proficiency</span>
        </div>
        <div class="chart-wrapper">
          <Bar v-if="chartDataReady" :key="themeStore.currentTheme" :data="barChartData" :options="barChartOptions" />
        </div>
      </div>

      <!-- Priority Breakdown Table -->
      <div class="card table-card">
        <div class="card-header">
          <h3 class="card-title">Detailed Gap Prioritization Table</h3>
          <span class="text-sm text-muted">Sorted by dependency-weighted priority score</span>
        </div>

        <EmptyState
          v-if="gapData.competencies?.length === 0"
          icon="🎉"
          title="No competencies mapped to this role"
        />

        <div v-else class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Competency</th>
                <th>Current Level</th>
                <th>Required Level</th>
                <th>Gap</th>
                <th>Priority Score</th>
                <th>Prerequisite Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in sortedCompetencies" :key="item.competency_id">
                <td>
                  <strong>{{ item.competency_name }}</strong>
                </td>
                <td>
                  <LevelBadge :level="item.current_level" :showName="true" />
                </td>
                <td>
                  <LevelBadge :level="item.required_level" :showName="true" />
                </td>
                <td>
                  <span v-if="item.gap > 0" class="gap-tag text-warning">
                    -{{ item.gap.toFixed(1) }}
                  </span>
                  <span v-else class="gap-tag text-success">Met ✓</span>
                </td>
                <td>
                  <strong>{{ item.priority }}</strong>
                </td>
                <td>
                  <div v-if="item.is_blocked" class="badge badge-danger">
                    ⚠️ Blocked by: {{ item.blocked_by.join(', ') }}
                  </div>
                  <div v-else-if="item.gap > 0" class="badge badge-info">
                    Ready to learn
                  </div>
                  <div v-else class="badge badge-success">
                    Qualified
                  </div>
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
import EmptyState from '@/components/common/EmptyState.vue'
import ProgressBar from '@/components/common/ProgressBar.vue'
import LevelBadge from '@/components/common/LevelBadge.vue'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const themeStore = useThemeStore()
const roles = ref([])
const selectedRoleId = ref(null)
const gapData = ref(null)
const isLoading = ref(true)
const errorMessage = ref('')

const sortedCompetencies = computed(() => {
  if (!gapData.value?.competencies) return []
  return [...gapData.value.competencies].sort((a, b) => b.priority - a.priority)
})

const chartDataReady = computed(() => {
  return gapData.value && gapData.value.competencies && gapData.value.competencies.length > 0
})

const barChartData = computed(() => {
  if (!chartDataReady.value) return { labels: [], datasets: [] }
  const comps = gapData.value.competencies
  const isDark = themeStore.isDark

  return {
    labels: comps.map((c) => c.competency_name),
    datasets: [
      {
        label: 'Current Assessed Level',
        backgroundColor: isDark ? '#3b82f6' : '#2563eb',
        borderRadius: 4,
        data: comps.map((c) => c.current_level)
      },
      {
        label: 'Required Role Level',
        backgroundColor: isDark ? '#334155' : '#cbd5e1',
        borderRadius: 4,
        data: comps.map((c) => c.required_level)
      }
    ]
  }
})

const barChartOptions = computed(() => {
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
        max: 5,
        ticks: {
          stepSize: 1,
          color: textMuted,
          font: { family: 'Inter' }
        },
        grid: {
          color: gridLine
        },
        title: {
          display: true,
          text: 'Proficiency Level (1-5)',
          color: textMuted
        }
      },
      x: {
        ticks: {
          color: textMuted,
          font: { family: 'Inter', size: 11 },
          maxRotation: 45,
          minRotation: 25
        },
        grid: {
          color: gridLine
        }
      }
    }
  }
})

const loadGapReport = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    if (roles.value.length === 0) {
      const res = await api.get('/roles')
      roles.value = res.roles || []
      if (roles.value.length > 0 && !selectedRoleId.value) {
        selectedRoleId.value = roles.value[0].id
      }
    }

    if (!selectedRoleId.value) {
      isLoading.value = false
      return
    }

    const data = await api.get(`/gap?role_id=${selectedRoleId.value}`)
    gapData.value = data
  } catch (err) {
    errorMessage.value = err.message || 'Failed to calculate gap report'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadGapReport()
})
</script>

<style scoped>
.gap-page {
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
  width: 260px;
}

.gap-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.readiness-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.readiness-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.readiness-score {
  font-size: 2.5rem;
  font-weight: 800;
  color: var(--color-accent);
}

.chart-card {
  min-height: 380px;
}

.chart-wrapper {
  position: relative;
  height: 320px;
  width: 100%;
}

.gap-tag {
  font-weight: 700;
  font-size: var(--font-size-sm);
}

.text-warning { color: var(--color-warning); }
.text-success { color: var(--color-success); }
</style>
