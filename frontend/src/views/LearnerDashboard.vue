<template>
  <div class="dashboard-page">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h1>Learner Dashboard</h1>
        <p>Monitor your competency readiness, priority gaps, and upcoming training modules.</p>
      </div>

      <div class="role-selector" v-if="roles.length">
        <label for="role-select" class="form-label" style="margin-bottom: 0;">Target Role:</label>
        <select id="role-select" v-model="selectedRoleId" @change="loadDashboardData" class="form-control select-role">
          <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
      </div>
    </div>

    <!-- Loading / Error states -->
    <LoadingState v-if="isLoading" message="Analyzing your competency portfolio..." />
    <ErrorState v-else-if="errorMessage" :message="errorMessage" @retry="loadDashboardData" />

    <div v-else class="dashboard-content">
      <!-- Top Overview Metrics -->
      <div class="grid-4 metrics-row">
        <!-- Metric 1: Readiness Score -->
        <div class="card metric-card">
          <div class="metric-label">Role Readiness</div>
          <div class="metric-value">{{ readinessPercentage }}%</div>
          <ProgressBar :percentage="readinessPercentage" :showLabel="false" :height="10" />
          <span class="metric-caption">Target Role: {{ activeRoleName }}</span>
        </div>

        <!-- Metric 2: Gaps Count -->
        <div class="card metric-card">
          <div class="metric-label">Identified Gaps</div>
          <div class="metric-value text-warning">{{ gapList.length }}</div>
          <span class="metric-caption">{{ blockedGapsCount }} blocked by prerequisites</span>
        </div>

        <!-- Metric 3: Next Recommended Course -->
        <div class="card metric-card">
          <div class="metric-label">Next Course</div>
          <div v-if="nextCourse" class="course-mini-preview">
            <strong class="course-title">{{ nextCourse.title }}</strong>
            <span class="badge badge-info">{{ nextCourse.competency }} · L{{ nextCourse.level }}</span>
          </div>
          <div v-else class="text-muted text-sm">All courses completed! 🎉</div>
          <router-link to="/path" class="metric-link">Go to Path &rarr;</router-link>
        </div>

        <!-- Metric 4: Latest Quiz Result -->
        <div class="card metric-card">
          <div class="metric-label">Latest Assessment</div>
          <div v-if="latestQuiz" class="quiz-mini-preview">
            <span class="metric-value text-accent">{{ Math.round(latestQuiz.score_pct || 0) }}%</span>
            <span class="quiz-comp">{{ latestQuiz.competency_name }}</span>
            <span class="quiz-date">{{ formatDate(latestQuiz.submitted_at) }}</span>
          </div>
          <div v-else class="text-muted text-sm">No quiz attempts yet</div>
          <router-link to="/quiz" class="metric-link">Take Quiz &rarr;</router-link>
        </div>
      </div>

      <!-- Main Dashboard Grid -->
      <div class="grid-2 dashboard-main-grid">
        <!-- Top Priority Gaps -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Priority Competency Gaps</h3>
            <router-link to="/gap" class="btn btn-outline btn-sm">Full Report</router-link>
          </div>

          <EmptyState
            v-if="topGaps.length === 0"
            icon="🎉"
            title="No Competency Gaps!"
            description="You have achieved or exceeded required levels for all competencies in this role."
          />

          <div v-else class="gap-list">
            <div v-for="item in topGaps" :key="item.competency_id" class="gap-item">
              <div class="gap-main">
                <div class="gap-header">
                  <span class="gap-name">{{ item.competency_name }}</span>
                  <div class="gap-badges">
                    <span v-if="item.is_blocked" class="badge badge-danger">
                      Blocked by: {{ item.blocked_by.join(', ') }}
                    </span>
                    <span class="badge badge-warning">Priority Score: {{ item.priority }}</span>
                  </div>
                </div>

                <div class="gap-levels">
                  <span>Current: <LevelBadge :level="item.current_level" /></span>
                  <span class="arrow">&rarr;</span>
                  <span>Required: <LevelBadge :level="item.required_level" /></span>
                  <span class="gap-size">Gap: {{ item.gap.toFixed(1) }}</span>
                </div>

                <ProgressBar :percentage="(item.current_level / item.required_level) * 100" :showLabel="false" :height="6" />
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Start & Actions -->
        <div class="card actions-card">
          <div class="card-header">
            <h3 class="card-title">Recommended Actions</h3>
          </div>

          <div class="action-items">
            <div class="action-box">
              <div class="action-icon">🎯</div>
              <div class="action-info">
                <h4>Diagnostic Assessment</h4>
                <p>Take a 3-question evaluation per role competency to pinpoint exact gaps.</p>
              </div>
              <router-link to="/quiz?mode=diagnostic" class="btn btn-primary btn-sm">
                Start Diagnostic
              </router-link>
            </div>

            <div class="action-box">
              <div class="action-icon">👤</div>
              <div class="action-info">
                <h4>Update Your Profile Text</h4>
                <p>Paste your bio, CV, or training certificates to extract evidenced skills automatically.</p>
              </div>
              <router-link to="/profile" class="btn btn-secondary btn-sm">
                Analyze Bio
              </router-link>
            </div>

            <div class="action-box">
              <div class="action-icon">🗺️</div>
              <div class="action-info">
                <h4>Structured Learning Path</h4>
                <p>Follow a DAG-ordered curriculum designed to resolve prerequisites first.</p>
              </div>
              <router-link to="/path" class="btn btn-secondary btn-sm">
                View Curriculum
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ProgressBar from '@/components/common/ProgressBar.vue'
import LevelBadge from '@/components/common/LevelBadge.vue'

const roles = ref([])
const selectedRoleId = ref(null)
const isLoading = ref(true)
const errorMessage = ref('')

const gapData = ref(null)
const nextCourse = ref(null)
const latestQuiz = ref(null)

const activeRoleName = computed(() => {
  const r = roles.value.find((x) => x.id === selectedRoleId.value)
  return r ? r.name : 'Selected Role'
})

const readinessPercentage = computed(() => {
  return Math.round(gapData.value?.readiness_percentage || 0)
})

const gapList = computed(() => {
  return gapData.value?.competencies?.filter((c) => c.gap > 0) || []
})

const topGaps = computed(() => {
  return gapList.value.slice(0, 3)
})

const blockedGapsCount = computed(() => {
  return gapList.value.filter((c) => c.is_blocked).length
})

const formatDate = (isoString) => {
  if (!isoString) return ''
  const d = new Date(isoString)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

const loadDashboardData = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    // 1. Load roles if not loaded
    if (roles.value.length === 0) {
      const rolesRes = await api.get('/roles')
      roles.value = rolesRes.roles || []
      if (roles.value.length > 0 && !selectedRoleId.value) {
        selectedRoleId.value = roles.value[0].id
      }
    }

    if (!selectedRoleId.value) {
      isLoading.value = false
      return
    }

    // 2. Load Gap Data, Learning Path, and Quiz History in parallel
    const [gapRes, pathRes, histRes] = await Promise.allSettled([
      api.get(`/gap?role_id=${selectedRoleId.value}`),
      api.get(`/path?role_id=${selectedRoleId.value}`),
      api.get('/quiz/history')
    ])

    if (gapRes.status === 'fulfilled') {
      gapData.value = gapRes.value
    } else {
      errorMessage.value = gapRes.reason?.message || 'Failed to load gap analysis'
    }

    if (pathRes.status === 'fulfilled') {
      const steps = pathRes.value?.path?.steps || []
      // Find first uncompleted course
      let found = null
      for (const step of steps) {
        const courses = step.courses || []
        const activeCourse = courses.find((c) => c.progress_status !== 'completed')
        if (activeCourse) {
          found = activeCourse
          break
        }
      }
      nextCourse.value = found
    }

    if (histRes.status === 'fulfilled') {
      const history = histRes.value?.history || []
      latestQuiz.value = history.length > 0 ? history[0] : null
    }
  } catch (err) {
    errorMessage.value = err.message || 'Failed to load dashboard data'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
.dashboard-page {
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

.metrics-row {
  margin-bottom: 0.5rem;
}

.metric-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 140px;
}

.metric-label {
  font-size: var(--font-size-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
}

.metric-value {
  font-size: 2.25rem;
  font-weight: 800;
  line-height: 1;
  margin: 0.5rem 0;
}

.metric-caption {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.metric-link {
  font-size: var(--font-size-xs);
  font-weight: 600;
  align-self: flex-start;
  margin-top: 0.5rem;
}

.text-warning { color: var(--color-warning); }
.text-accent { color: var(--color-accent); }

.course-mini-preview, .quiz-mini-preview {
  margin: 0.25rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.course-title {
  font-size: var(--font-size-sm);
  color: var(--color-text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.quiz-comp {
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.quiz-date {
  font-size: 0.6875rem;
  color: var(--color-text-light);
}

.gap-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.gap-item {
  padding: 1rem;
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.gap-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.5rem;
}

.gap-name {
  font-weight: 700;
  font-size: var(--font-size-sm);
  color: var(--color-text-main);
}

.gap-badges {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.gap-levels {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: var(--font-size-xs);
  margin-bottom: 0.5rem;
}

.arrow {
  color: var(--color-text-muted);
}

.gap-size {
  margin-left: auto;
  font-weight: 700;
  color: var(--color-warning);
}

.action-items {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.action-box {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-bg);
}

.action-icon {
  font-size: 1.75rem;
}

.action-info {
  flex: 1;
}

.action-info h4 {
  font-size: var(--font-size-sm);
  margin-bottom: 0.2rem;
}

.action-info p {
  font-size: var(--font-size-xs);
  margin-bottom: 0;
}
</style>
