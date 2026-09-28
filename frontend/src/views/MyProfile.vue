<template>
  <div class="profile-page">
    <div class="page-header">
      <div>
        <h1>My Profile & Competencies</h1>
        <p>Extract verified competencies from your resume/bio, submit self-assessments, and view your unified skill portfolio.</p>
      </div>
    </div>

    <!-- Feedback Message Banner -->
    <div v-if="feedbackMessage" class="feedback-banner" :class="feedbackType">
      {{ feedbackMessage }}
    </div>

    <div class="tabs-nav">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'combined' }"
        @click="activeTab = 'combined'"
      >
        🌟 Combined Skills ({{ combinedSkillsList.length }})
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'analyze' }"
        @click="activeTab = 'analyze'"
      >
        📄 AI Profile Extraction
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'self' }"
        @click="activeTab = 'self'"
      >
        ✏️ Self-Assessment
      </button>
    </div>

    <!-- TAB 1: COMBINED SKILLS -->
    <div v-if="activeTab === 'combined'" class="tab-content">
      <LoadingState v-if="isLoadingSkills" message="Loading your unified skills..." />
      <ErrorState v-else-if="skillsError" :message="skillsError" @retry="loadCombinedSkills" />
      <div v-else class="card">
        <div class="card-header">
          <h3 class="card-title">Unified Competency Portfolio</h3>
          <span class="text-sm text-muted">Quiz scores take priority, blended with profile and self ratings.</span>
        </div>

        <EmptyState
          v-if="combinedSkillsList.length === 0"
          icon="📝"
          title="No skills recorded yet"
          description="Analyze your profile text or complete a self-assessment to initialize your skill ratings."
        >
          <template #action>
            <button class="btn btn-primary btn-sm" @click="activeTab = 'analyze'">
              Analyze Profile Text
            </button>
          </template>
        </EmptyState>

        <div v-else class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Competency</th>
                <th>Assessed Level</th>
                <th>Contributing Sources</th>
                <th>Source Breakdown</th>
                <th>Evidence & Rationale</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="skill in combinedSkillsList" :key="skill.competency_id">
                <td>
                  <strong>{{ skill.competency_name }}</strong>
                </td>
                <td>
                  <LevelBadge :level="skill.level" :showName="true" />
                </td>
                <td>
                  <div class="badge-group">
                    <span
                      v-for="src in skill.sources"
                      :key="src"
                      class="badge"
                      :class="getSourceBadgeClass(src)"
                    >
                      {{ src }}
                    </span>
                  </div>
                </td>
                <td>
                  <div class="breakdown-list">
                    <span v-for="(val, src) in skill.source_breakdown" :key="src" class="breakdown-item">
                      {{ src }}: <strong>L{{ val }}</strong>
                    </span>
                  </div>
                </td>
                <td>
                  <div class="evidence-snippet">
                    <span v-if="skill.evidence && skill.evidence.length">
                      {{ skill.evidence[0] }}
                    </span>
                    <span v-else class="text-muted">No evidence sentences attached</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 2: AI PROFILE EXTRACTION -->
    <div v-if="activeTab === 'analyze'" class="tab-content">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Analyze Resume / Profile Text</h3>
          <span class="text-sm text-muted">Powered by BAAI semantic embeddings</span>
        </div>

        <p class="section-desc">
          Paste your professional biography, duties in official surveys (NSS/ASI), or project descriptions. The system detects matching MoSPI competencies, extracts evidence sentences, and transparently estimates proficiency (Levels 1–4).
        </p>

        <div class="form-group">
          <label class="form-label" for="bio-text">Profile Description / Experience:</label>
          <textarea
            id="bio-text"
            v-model="profileText"
            class="form-control"
            rows="6"
            placeholder="e.g. Conducted nationwide field surveys and stratified sampling schemes for the Annual Survey of Industries. Extensively utilized SQL for database querying and Python for statistical regression and data cleaning over 4 years..."
          ></textarea>
        </div>

        <button class="btn btn-primary" :disabled="isAnalyzing || !profileText.trim()" @click="analyzeProfile">
          <span v-if="isAnalyzing">Analyzing Sentences...</span>
          <span v-else>🔍 Extract Competencies</span>
        </button>

        <!-- Matched Competencies Output -->
        <div v-if="extractedCompetencies.length > 0" class="extracted-results">
          <div class="results-header">
            <h4>Extracted Competencies ({{ extractedCompetencies.length }})</h4>
            <button class="btn btn-success btn-sm" :disabled="isSavingProfile" @click="saveExtractedSkills">
              <span v-if="isSavingProfile">Saving...</span>
              <span v-else>💾 Save to My Profile</span>
            </button>
          </div>

          <div class="extracted-grid">
            <div
              v-for="item in extractedCompetencies"
              :key="item.competency_id"
              class="extracted-card"
            >
              <div class="extracted-top">
                <span class="comp-title">{{ item.competency_name }}</span>
                <LevelBadge :level="item.estimated_level" :showName="true" />
              </div>

              <!-- Evidence sentences -->
              <div class="evidence-box">
                <span class="evidence-label">Evidence:</span>
                <ul>
                  <li v-for="(sentence, i) in item.evidence" :key="i">
                    "{{ sentence }}"
                  </li>
                </ul>
              </div>

              <!-- Rule Reasons -->
              <div class="reasons-box">
                <span class="reasons-label">Level Estimation Logic:</span>
                <div class="reasons-tags">
                  <span v-for="(r, idx) in item.reasons" :key="idx" class="badge badge-info">
                    {{ r }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: SELF-ASSESSMENT -->
    <div v-if="activeTab === 'self'" class="tab-content">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Competency Self-Assessment</h3>
          <span class="text-sm text-muted">Rate your self-perceived proficiency from Level 1 to 5</span>
        </div>

        <LoadingState v-if="isLoadingAllCompetencies" message="Loading competency catalogue..." />
        <form v-else @submit.prevent="submitSelfAssessment" class="self-assess-form">
          <div v-for="comp in allCompetencies" :key="comp.id" class="self-assess-row">
            <div class="self-comp-info">
              <strong>{{ comp.name }}</strong>
              <p>{{ comp.description }}</p>
            </div>

            <div class="self-rating-selector">
              <label
                v-for="lvl in [1, 2, 3, 4, 5]"
                :key="lvl"
                class="rating-btn"
                :class="{ selected: selfRatings[comp.id] === lvl }"
              >
                <input
                  type="radio"
                  :name="'comp_' + comp.id"
                  :value="lvl"
                  v-model="selfRatings[comp.id]"
                />
                L{{ lvl }}
              </label>
            </div>
          </div>

          <div class="form-actions">
            <button type="submit" class="btn btn-primary" :disabled="isSubmittingSelf">
              <span v-if="isSubmittingSelf">Saving...</span>
              <span v-else>Save Self-Assessment</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LevelBadge from '@/components/common/LevelBadge.vue'

const activeTab = ref('combined')

// Tab 1: Combined Skills
const combinedSkillsList = ref([])
const isLoadingSkills = ref(false)
const skillsError = ref('')

// Tab 2: Profile Extraction
const profileText = ref('')
const isAnalyzing = ref(false)
const isSavingProfile = ref(false)
const extractedCompetencies = ref([])

// Tab 3: Self-Assessment
const allCompetencies = ref([])
const isLoadingAllCompetencies = ref(false)
const selfRatings = reactive({})
const isSubmittingSelf = ref(false)

// Banner Feedback
const feedbackMessage = ref('')
const feedbackType = ref('success')

const showFeedback = (msg, type = 'success') => {
  feedbackMessage.value = msg
  feedbackType.value = type
  setTimeout(() => {
    feedbackMessage.value = ''
  }, 4000)
}

const getSourceBadgeClass = (source) => {
  if (source === 'quiz') return 'badge-success'
  if (source === 'profile') return 'badge-info'
  return 'badge-warning'
}

// 1. Load Combined Skills
const loadCombinedSkills = async () => {
  isLoadingSkills.value = true
  skillsError.value = ''
  try {
    const res = await api.get('/profile/skills')
    combinedSkillsList.value = res.skills || []
  } catch (err) {
    skillsError.value = err.message || 'Failed to load skills'
  } finally {
    isLoadingSkills.value = false
  }
}

// 2. Profile Extraction
const analyzeProfile = async () => {
  if (!profileText.value.trim()) return
  isAnalyzing.value = true
  try {
    const res = await api.post('/profile/analyze', { text: profileText.value })
    extractedCompetencies.value = res.matches || []
    if (extractedCompetencies.value.length === 0) {
      showFeedback('No competencies matched above threshold. Try adding more specific statistical tools or keywords.', 'warning')
    }
  } catch (err) {
    showFeedback(err.message || 'Analysis failed', 'danger')
  } finally {
    isAnalyzing.value = false
  }
}

const saveExtractedSkills = async () => {
  if (extractedCompetencies.value.length === 0) return
  isSavingProfile.value = true
  try {
    const skillsToSave = extractedCompetencies.value.map((m) => ({
      competency_id: m.competency_id,
      level: m.estimated_level,
      evidence: { sentences: m.evidence, reasons: m.reasons }
    }))
    await api.post('/profile/skills', { skills: skillsToSave })
    showFeedback('Skills successfully saved to your profile!', 'success')
    await loadCombinedSkills()
    activeTab.value = 'combined'
  } catch (err) {
    showFeedback(err.message || 'Failed to save skills', 'danger')
  } finally {
    isSavingProfile.value = false
  }
}

// 3. Self-Assessment
const loadAllCompetencies = async () => {
  isLoadingAllCompetencies.value = true
  try {
    const res = await api.get('/competencies')
    allCompetencies.value = res.competencies || []
    // Initialize existing ratings if present
    for (const c of allCompetencies.value) {
      const existing = combinedSkillsList.value.find((s) => s.competency_id === c.id)
      selfRatings[c.id] = existing ? Math.round(existing.level) : 1
    }
  } catch (err) {
    showFeedback(err.message || 'Failed to load competencies', 'danger')
  } finally {
    isLoadingAllCompetencies.value = false
  }
}

const submitSelfAssessment = async () => {
  isSubmittingSelf.value = true
  try {
    const ratings = {}
    for (const [id, lvl] of Object.entries(selfRatings)) {
      ratings[id] = Number(lvl)
    }
    await api.post('/profile/self-assess', { ratings })
    showFeedback('Self-assessment updated successfully!', 'success')
    await loadCombinedSkills()
    activeTab.value = 'combined'
  } catch (err) {
    showFeedback(err.message || 'Failed to submit self-assessment', 'danger')
  } finally {
    isSubmittingSelf.value = false
  }
}

onMounted(() => {
  loadCombinedSkills()
  loadAllCompetencies()
})
</script>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.feedback-banner {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.feedback-banner.success {
  background-color: var(--color-success-light);
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.feedback-banner.warning {
  background-color: var(--color-warning-light);
  color: #92400e;
  border: 1px solid #fde68a;
}

.feedback-banner.danger {
  background-color: var(--color-danger-light);
  color: #991b1b;
  border: 1px solid #fecaca;
}

.tabs-nav {
  display: flex;
  gap: 0.5rem;
  border-bottom: 2px solid var(--color-border);
  padding-bottom: 2px;
}

.tab-btn {
  background: none;
  border: none;
  padding: 0.625rem 1.25rem;
  font-family: inherit;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-muted);
  cursor: pointer;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  color: var(--color-text-main);
  background-color: var(--color-surface-hover);
}

.tab-btn.active {
  color: var(--color-accent);
  background-color: var(--color-surface);
  border-bottom: 3px solid var(--color-accent);
}

.badge-group {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.breakdown-list {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: var(--font-size-xs);
}

.evidence-snippet {
  max-width: 320px;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  line-height: 1.4;
}

.section-desc {
  font-size: var(--font-size-sm);
  margin-bottom: 1.25rem;
  line-height: 1.6;
}

.extracted-results {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--color-border);
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.extracted-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.extracted-card {
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.extracted-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.comp-title {
  font-weight: 700;
  font-size: var(--font-size-sm);
}

.evidence-box, .reasons-box {
  font-size: var(--font-size-xs);
}

.evidence-label, .reasons-label {
  font-weight: 700;
  color: var(--color-text-muted);
  display: block;
  margin-bottom: 0.25rem;
}

.evidence-box ul {
  padding-left: 1.2rem;
  color: var(--color-text-main);
  font-style: italic;
}

.reasons-tags {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.self-assess-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.self-assess-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  gap: 1.5rem;
}

.self-comp-info {
  flex: 1;
}

.self-comp-info p {
  font-size: var(--font-size-xs);
  margin-top: 0.25rem;
}

.self-rating-selector {
  display: flex;
  gap: 0.5rem;
}

.rating-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 38px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-weight: 700;
  font-size: var(--font-size-xs);
  cursor: pointer;
  background-color: #ffffff;
  transition: all var(--transition-fast);
}

.rating-btn input {
  display: none;
}

.rating-btn:hover {
  background-color: var(--color-surface-hover);
}

.rating-btn.selected {
  background-color: var(--color-accent);
  color: #ffffff;
  border-color: var(--color-accent);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1rem;
}
</style>
