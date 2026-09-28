<template>
  <div class="path-page">
    <div class="page-header">
      <div>
        <h1>Personalized Learning Path</h1>
        <p>Curated sequence of iGOT Karmayogi modules ordered topologically to resolve dependencies first.</p>
      </div>

      <div class="header-actions">
        <div class="role-selector" v-if="roles.length">
          <label for="path-role-select" class="form-label" style="margin-bottom: 0;">Role:</label>
          <select
            id="path-role-select"
            v-model="selectedRoleId"
            @change="loadLearningPath"
            class="form-control select-role"
          >
            <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </div>

        <div v-if="pathData && pathData.total_hours" class="total-hours-badge">
          ⏱️ <strong>{{ pathData.total_hours }}</strong> Total Hours
        </div>
      </div>
    </div>

    <LoadingState v-if="isLoading" message="Generating topological curriculum..." />
    <ErrorState v-else-if="errorMessage" :message="errorMessage" @retry="loadLearningPath" />

    <div v-else-if="pathData" class="path-content">
      <!-- Empty State when no gaps remain -->
      <EmptyState
        v-if="!pathData.steps || pathData.steps.length === 0"
        icon="🎓"
        title="Path Complete!"
        description="You have no remaining competency gaps or uncompleted courses for this role. Excellent work!"
      />

      <!-- Grouped by Stage: Foundation -> Core -> Advanced -->
      <div v-else class="stages-container">
        <div
          v-for="stage in activeStages"
          :key="stage.name"
          class="stage-block"
        >
          <div class="stage-header">
            <div class="stage-tag" :class="stage.badgeClass">
              {{ stage.name }} Stage
            </div>
            <span class="stage-count text-sm text-muted">
              {{ stage.steps.length }} competency step(s)
            </span>
          </div>

          <!-- Steps within stage -->
          <div class="steps-list">
            <div
              v-for="(step, idx) in stage.steps"
              :key="step.competency_id"
              class="card step-card"
            >
              <div class="step-meta">
                <div class="step-num">Step {{ step.step_order || (idx + 1) }}</div>
                <div class="step-title-row">
                  <h3 class="step-comp-name">{{ step.competency_name }}</h3>
                  <div class="step-levels">
                    <LevelBadge :level="step.current_level" :showName="true" />
                    <span class="arrow">&rarr;</span>
                    <LevelBadge :level="step.target_level" :showName="true" />
                  </div>
                </div>

                <!-- Data-driven "Why" explanation -->
                <div class="step-why">
                  <span class="why-icon">💡</span>
                  <span class="why-text"><strong>Rationale:</strong> {{ step.why }}</span>
                </div>
              </div>

              <!-- Recommended Courses for this step -->
              <div class="courses-section">
                <h4 class="courses-heading">
                  Recommended Courses ({{ step.courses?.length || 0 }})
                </h4>

                <div class="courses-grid">
                  <div
                    v-for="course in step.courses"
                    :key="course.id"
                    class="course-card"
                    :class="{ 'course-completed': course.progress_status === 'completed' }"
                  >
                    <div class="course-top">
                      <span class="course-provider">{{ course.provider || 'iGOT Karmayogi' }}</span>
                      <span class="course-duration">⏱️ {{ course.duration_hours }}h</span>
                    </div>

                    <h5 class="course-title">{{ course.title }}</h5>
                    <p class="course-desc">{{ course.description }}</p>

                    <div class="course-footer">
                      <LevelBadge :level="course.level" />

                      <!-- Course Progress Buttons -->
                      <div class="progress-actions">
                        <button
                          class="status-btn"
                          :class="{ active: course.progress_status === 'planned' }"
                          @click="updateCourseProgress(course.id, 'planned')"
                          title="Mark Planned"
                        >
                          Planned
                        </button>
                        <button
                          class="status-btn"
                          :class="{ active: course.progress_status === 'in_progress' }"
                          @click="updateCourseProgress(course.id, 'in_progress')"
                          title="Mark In Progress"
                        >
                          In Progress
                        </button>
                        <button
                          class="status-btn btn-check"
                          :class="{ active: course.progress_status === 'completed' }"
                          @click="updateCourseProgress(course.id, 'completed')"
                          title="Mark Completed"
                        >
                          ✓ Done
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
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
import LevelBadge from '@/components/common/LevelBadge.vue'

const roles = ref([])
const selectedRoleId = ref(null)
const pathData = ref(null)
const isLoading = ref(true)
const errorMessage = ref('')

const activeStages = computed(() => {
  if (!pathData.value?.steps) return []

  const stagesDef = [
    { name: 'Foundation', badgeClass: 'badge-info', steps: [] },
    { name: 'Core', badgeClass: 'badge-warning', steps: [] },
    { name: 'Advanced', badgeClass: 'badge-success', steps: [] }
  ]

  for (const step of pathData.value.steps) {
    const stageName = step.stage || 'Foundation'
    const target = stagesDef.find((s) => s.name.toLowerCase() === stageName.toLowerCase())
    if (target) {
      target.steps.push(step)
    } else {
      stagesDef[0].steps.push(step)
    }
  }

  return stagesDef.filter((s) => s.steps.length > 0)
})

const loadLearningPath = async () => {
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

    const data = await api.get(`/path?role_id=${selectedRoleId.value}`)
    pathData.value = data.path || data
  } catch (err) {
    errorMessage.value = err.message || 'Failed to load learning path'
  } finally {
    isLoading.value = false
  }
}

const updateCourseProgress = async (courseId, status) => {
  try {
    await api.post('/path/progress', { course_id: courseId, status })
    // Refresh the path to exclude completed courses or update state
    await loadLearningPath()
  } catch (err) {
    alert(err.message || 'Failed to update progress')
  }
}

onMounted(() => {
  loadLearningPath()
})
</script>

<style scoped>
.path-page {
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.select-role {
  width: 240px;
}

.total-hours-badge {
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
}

.stages-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.stage-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.stage-tag {
  font-size: var(--font-size-sm);
  font-weight: 700;
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-full);
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.step-card {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.step-meta {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.step-num {
  font-size: var(--font-size-xs);
  font-weight: 800;
  text-transform: uppercase;
  color: var(--color-accent);
  letter-spacing: 0.05em;
}

.step-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.step-comp-name {
  font-size: var(--font-size-lg);
  font-weight: 700;
}

.step-levels {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.arrow {
  color: var(--color-text-muted);
}

.step-why {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  background-color: var(--color-bg);
  border-left: 3px solid var(--color-accent);
  padding: 0.625rem 0.875rem;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-main);
  line-height: 1.5;
}

.why-icon {
  flex-shrink: 0;
}

.courses-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  border-top: 1px solid var(--color-border);
  padding-top: 1rem;
}

.courses-heading {
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
}

.courses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.course-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-bg);
  transition: all var(--transition-fast);
}

.course-card:hover {
  border-color: var(--color-accent);
}

.course-completed {
  opacity: 0.7;
  border-style: dashed;
}

.course-top {
  display: flex;
  justify-content: space-between;
  font-size: 0.6875rem;
  color: var(--color-text-light);
  margin-bottom: 0.35rem;
}

.course-title {
  font-size: var(--font-size-sm);
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.course-desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  line-height: 1.4;
  margin-bottom: 0.75rem;
}

.course-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  padding-top: 0.5rem;
  border-top: 1px solid var(--color-border);
}

.progress-actions {
  display: flex;
  gap: 0.25rem;
}

.status-btn {
  background: #ffffff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 0.2rem 0.4rem;
  font-size: 0.6875rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.status-btn:hover {
  background: var(--color-surface-hover);
}

.status-btn.active {
  background: var(--color-accent);
  color: #ffffff;
  border-color: var(--color-accent);
}

.status-btn.btn-check.active {
  background: var(--color-success);
  border-color: var(--color-success);
}
</style>
