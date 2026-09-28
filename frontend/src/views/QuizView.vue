<template>
  <div class="quiz-page">
    <!-- Header -->
    <div class="page-header" v-if="state === 'setup'">
      <div>
        <h1>Competency Assessments & Quizzes</h1>
        <p>Validate your official statistical knowledge with document-grounded multiple-choice quizzes.</p>
      </div>
    </div>

    <!-- Feedback Banner -->
    <div v-if="feedbackError" class="error-banner">
      {{ feedbackError }}
    </div>

    <!-- ========================================================
         STATE 1: SETUP SCREEN (SELECT COMPETENCY OR DIAGNOSTIC)
         ======================================================== -->
    <div v-if="state === 'setup'" class="setup-container">
      <div class="grid-2">
        <!-- Single Competency Quiz Setup -->
        <div class="card setup-card">
          <div class="card-header">
            <h3 class="card-title">Specific Competency Quiz</h3>
            <span class="badge badge-info">Adaptive</span>
          </div>

          <p class="setup-desc">
            Test yourself on a single domain. Quizzes balance easy, medium, and hard questions and avoid recently solved items.
          </p>

          <div class="form-group">
            <label class="form-label" for="select-comp">Select Competency:</label>
            <select id="select-comp" v-model="selectedCompId" class="form-control">
              <option v-for="c in competencies" :key="c.id" :value="c.id">
                {{ c.name }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label" for="select-n">Number of Questions:</label>
            <select id="select-n" v-model.number="questionCount" class="form-control">
              <option :value="3">3 Questions (Quick check)</option>
              <option :value="5">5 Questions (Standard session)</option>
              <option :value="10">10 Questions (Comprehensive check)</option>
            </select>
          </div>

          <button
            class="btn btn-primary btn-lg"
            :disabled="isStarting || !selectedCompId"
            @click="startStandardQuiz"
          >
            <span v-if="isStarting">Preparing Session...</span>
            <span v-else>Start Assessment &rarr;</span>
          </button>
        </div>

        <!-- Role Diagnostic Mode Setup -->
        <div class="card setup-card diagnostic-card">
          <div class="card-header">
            <h3 class="card-title">Role Diagnostic Mode</h3>
            <span class="badge badge-warning">All Competencies</span>
          </div>

          <p class="setup-desc">
            Take a 3-question evaluation across every required competency for a job role to benchmark your baseline readiness.
          </p>

          <div class="form-group">
            <label class="form-label" for="select-diag-role">Target Role:</label>
            <select id="select-diag-role" v-model="selectedDiagRoleId" class="form-control">
              <option v-for="r in roles" :key="r.id" :value="r.id">
                {{ r.name }}
              </option>
            </select>
          </div>

          <button
            class="btn btn-secondary btn-lg"
            :disabled="isStartingDiag || !selectedDiagRoleId"
            @click="startDiagnosticMode"
          >
            <span v-if="isStartingDiag">Loading Diagnostic...</span>
            <span v-else>Launch Full Diagnostic 🎯</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ========================================================
         STATE 2: ACTIVE QUIZ IN PROGRESS
         ======================================================== -->
    <div v-else-if="state === 'active'" class="active-quiz-container">
      <div class="quiz-topbar card">
        <div class="quiz-topbar-info">
          <span class="quiz-comp-name">{{ activeSessionTitle }}</span>
          <span class="quiz-counter">
            Question <strong>{{ currentQuestionIndex + 1 }}</strong> of {{ activeQuestions.length }}
          </span>
        </div>
        <ProgressBar
          :percentage="((currentQuestionIndex + 1) / activeQuestions.length) * 100"
          :showLabel="false"
          :height="6"
        />
      </div>

      <!-- Current Question Card -->
      <div class="card question-card" v-if="currentQuestion">
        <div class="question-header">
          <div class="question-text">{{ currentQuestion.text }}</div>
          <span class="badge badge-info">{{ currentQuestion.difficulty || 'medium' }}</span>
        </div>

        <!-- 4 Options -->
        <div class="options-container">
          <button
            v-for="(optionText, idx) in currentQuestion.options"
            :key="idx"
            class="option-item"
            :class="{ selected: selectedAnswers[currentQuestion.id] === idx }"
            @click="selectAnswer(currentQuestion.id, idx)"
          >
            <span class="option-marker">{{ String.fromCharCode(65 + idx) }}</span>
            <span class="option-text">{{ optionText }}</span>
          </button>
        </div>

        <!-- Navigation Buttons -->
        <div class="quiz-nav-row">
          <button
            class="btn btn-secondary"
            :disabled="currentQuestionIndex === 0"
            @click="currentQuestionIndex--"
          >
            &larr; Previous
          </button>

          <div class="quiz-nav-right">
            <button
              v-if="currentQuestionIndex < activeQuestions.length - 1"
              class="btn btn-primary"
              @click="currentQuestionIndex++"
            >
              Next &rarr;
            </button>
            <button
              v-else
              class="btn btn-primary btn-submit"
              :disabled="isSubmitting"
              @click="submitQuiz"
            >
              <span v-if="isSubmitting">Evaluating Answers...</span>
              <span v-else>Submit Assessment ✓</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ========================================================
         STATE 3: RESULTS & EXPLANATION REVIEW
         ======================================================== -->
    <div v-else-if="state === 'results'" class="results-container">
      <div class="card results-summary-card">
        <div class="summary-top">
          <div>
            <h2>Assessment Results</h2>
            <p class="text-muted">{{ activeSessionTitle }}</p>
          </div>
          <div class="score-badge-big">
            {{ Math.round(resultsData.score_pct || 0) }}%
          </div>
        </div>

        <div class="level-transition-box">
          <div class="level-transition-item">
            <span class="lvl-label">Previous Level:</span>
            <LevelBadge :level="resultsData.level_before || 1" :showName="true" />
          </div>
          <div class="transition-arrow">&rarr;</div>
          <div class="level-transition-item">
            <span class="lvl-label">New Assessed Level:</span>
            <LevelBadge :level="resultsData.new_level || resultsData.level_after || 1" :showName="true" />
          </div>
        </div>

        <div class="results-actions">
          <button class="btn btn-primary" @click="resetToSetup">
            Take Another Assessment
          </button>
          <router-link to="/dashboard" class="btn btn-secondary">
            Go to Dashboard
          </router-link>
        </div>
      </div>

      <!-- Question-by-Question Detailed Review -->
      <div class="review-section">
        <h3>Question Explanations & Citations</h3>
        <p class="text-sm text-muted">All answers are cross-checked against source documents.</p>

        <div class="review-list">
          <div
            v-for="(item, idx) in resultsData.question_results"
            :key="item.question_id"
            class="card review-card"
            :class="item.is_correct ? 'correct-border' : 'incorrect-border'"
          >
            <div class="review-header">
              <span class="review-num">Q{{ idx + 1 }}</span>
              <div class="review-status">
                <span v-if="item.is_correct" class="badge badge-success">✓ Correct</span>
                <span v-else class="badge badge-danger">✗ Incorrect</span>
              </div>
            </div>

            <h4 class="review-q-text">{{ item.text }}</h4>

            <!-- Options Review -->
            <div class="review-options">
              <div
                v-for="(opt, optIdx) in item.options"
                :key="optIdx"
                class="review-opt"
                :class="{
                  'opt-correct': optIdx === item.correct_index,
                  'opt-chosen-wrong': !item.is_correct && optIdx === item.chosen_index
                }"
              >
                <span class="opt-label">{{ String.fromCharCode(65 + optIdx) }}</span>
                <span>{{ opt }}</span>
                <span v-if="optIdx === item.correct_index" class="opt-tag tag-correct">Correct Answer</span>
                <span v-else-if="optIdx === item.chosen_index" class="opt-tag tag-wrong">Your Answer</span>
              </div>
            </div>

            <!-- Explanation -->
            <div class="explanation-box" v-if="item.explanation">
              <strong>Explanation:</strong> {{ item.explanation }}
            </div>

            <!-- Source Passage Attribution -->
            <div class="citation-box" v-if="item.source_passage">
              <span class="citation-label">Source Document Passage:</span>
              <blockquote class="citation-quote">
                "{{ item.source_passage }}"
              </blockquote>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import ProgressBar from '@/components/common/ProgressBar.vue'
import LevelBadge from '@/components/common/LevelBadge.vue'

const route = useRoute()

// States: 'setup' | 'active' | 'results'
const state = ref('setup')

// Setup state
const competencies = ref([])
const roles = ref([])
const selectedCompId = ref(null)
const selectedDiagRoleId = ref(null)
const questionCount = ref(5)
const isStarting = ref(false)
const isStartingDiag = ref(false)
const feedbackError = ref('')

// Active Quiz state
const activeSessionId = ref(null)
const activeSessionTitle = ref('')
const activeQuestions = ref([])
const currentQuestionIndex = ref(0)
const selectedAnswers = reactive({})
const isSubmitting = ref(false)

// Diagnostic mode specific tracking
const isDiagnosticMode = ref(false)
const diagnosticSessions = ref([])

// Results state
const resultsData = ref({})

const currentQuestion = computed(() => {
  return activeQuestions.value[currentQuestionIndex.value] || null
})

const selectAnswer = (questionId, optionIdx) => {
  selectedAnswers[questionId] = optionIdx
}

// 1. Start Standard Quiz
const startStandardQuiz = async () => {
  if (!selectedCompId.value) return
  isStarting.value = true
  feedbackError.value = ''
  try {
    const res = await api.post(`/quiz/${selectedCompId.value}/start`, {
      n: questionCount.value
    })
    activeSessionId.value = res.session_id
    activeSessionTitle.value = res.competency_name || 'Competency Quiz'
    activeQuestions.value = res.questions || []
    currentQuestionIndex.value = 0
    isDiagnosticMode.value = false

    // Clear answers
    for (const key in selectedAnswers) delete selectedAnswers[key]

    state.value = 'active'
  } catch (err) {
    feedbackError.value = err.message || 'Failed to start quiz session'
  } finally {
    isStarting.value = false
  }
}

// 2. Start Diagnostic Mode
const startDiagnosticMode = async () => {
  if (!selectedDiagRoleId.value) return
  isStartingDiag.value = true
  feedbackError.value = ''
  try {
    const res = await api.post(`/diagnostic/start?role_id=${selectedDiagRoleId.value}`)
    diagnosticSessions.value = res.sessions || []

    if (diagnosticSessions.value.length === 0) {
      feedbackError.value = 'No competencies in this role currently have enough approved questions for diagnostic.'
      return
    }

    // Flatten all questions into a single cohesive assessment
    activeQuestions.value = []
    for (const sess of diagnosticSessions.value) {
      for (const q of sess.questions) {
        q._session_id = sess.session_id
        q._comp_name = sess.competency_name
        activeQuestions.value.push(q)
      }
    }

    activeSessionTitle.value = `Diagnostic: ${res.role_name}`
    currentQuestionIndex.value = 0
    isDiagnosticMode.value = true

    for (const key in selectedAnswers) delete selectedAnswers[key]
    state.value = 'active'
  } catch (err) {
    feedbackError.value = err.message || 'Failed to start diagnostic'
  } finally {
    isStartingDiag.value = false
  }
}

// 3. Submit Quiz
const submitQuiz = async () => {
  isSubmitting.value = true
  feedbackError.value = ''
  try {
    if (isDiagnosticMode.value) {
      // Group answers by session
      const submissions = diagnosticSessions.value.map((sess) => {
        const sessAnswers = {}
        for (const q of sess.questions) {
          sessAnswers[q.id] = selectedAnswers[q.id] ?? -1
        }
        return {
          session_id: sess.session_id,
          answers: sessAnswers
        }
      })

      const res = await api.post('/diagnostic/submit', {
        role_id: selectedDiagRoleId.value,
        sessions: submissions
      })

      // Aggregate all question results
      const allQResults = []
      let totalCorrect = 0
      let totalQ = 0

      for (const sRes of res.session_results || []) {
        totalCorrect += sRes.correct_count || 0
        totalQ += sRes.total_questions || 0
        allQResults.push(...(sRes.question_results || []))
      }

      resultsData.value = {
        score_pct: totalQ > 0 ? (totalCorrect / totalQ) * 100 : 0,
        level_before: 1,
        new_level: Math.round(totalQ > 0 ? (totalCorrect / totalQ) * 5 : 1),
        question_results: allQResults
      }
    } else {
      const res = await api.post(`/quiz/session/${activeSessionId.value}/submit`, {
        answers: { ...selectedAnswers }
      })
      resultsData.value = res.result || res
    }

    state.value = 'results'
  } catch (err) {
    feedbackError.value = err.message || 'Submission failed'
  } finally {
    isSubmitting.value = false
  }
}

const resetToSetup = () => {
  state.value = 'setup'
  resultsData.value = {}
  activeQuestions.value = []
  activeSessionId.value = null
}

onMounted(async () => {
  try {
    const [compRes, roleRes] = await Promise.all([
      api.get('/competencies'),
      api.get('/roles')
    ])
    competencies.value = compRes.competencies || []
    roles.value = roleRes.roles || []

    if (competencies.value.length > 0) {
      selectedCompId.value = competencies.value[0].id
    }
    if (roles.value.length > 0) {
      selectedDiagRoleId.value = roles.value[0].id
    }

    if (route.query.mode === 'diagnostic') {
      selectedDiagRoleId.value = roles.value[0]?.id
    }
  } catch {
    feedbackError.value = 'Failed to load competencies or roles'
  }
})
</script>

<style scoped>
.quiz-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-width: 900px;
  margin: 0 auto;
}

.error-banner {
  background-color: var(--color-danger-light);
  color: #b91c1c;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  border: 1px solid #fecaca;
}

.setup-card {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.setup-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  line-height: 1.5;
}

.diagnostic-card {
  border-left: 4px solid var(--color-warning);
}

.active-quiz-container {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.quiz-topbar {
  padding: 1rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.quiz-topbar-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quiz-comp-name {
  font-weight: 700;
  font-size: var(--font-size-base);
}

.quiz-counter {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.question-card {
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.question-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.question-text {
  font-size: var(--font-size-lg);
  font-weight: 700;
  line-height: 1.4;
}

.options-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background-color: #ffffff;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  font-size: var(--font-size-sm);
  transition: all var(--transition-fast);
}

.option-item:hover {
  background-color: var(--color-surface-hover);
  border-color: var(--color-border-subtle);
}

.option-item.selected {
  background-color: var(--color-accent-light);
  border-color: var(--color-accent);
}

.option-marker {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  font-weight: 700;
  font-size: var(--font-size-xs);
  flex-shrink: 0;
}

.option-item.selected .option-marker {
  background-color: var(--color-accent);
  color: #ffffff;
  border-color: var(--color-accent);
}

.option-text {
  flex: 1;
  color: var(--color-text-main);
  font-weight: 500;
}

.quiz-nav-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}

.quiz-nav-right {
  display: flex;
  gap: 0.5rem;
}

.results-summary-card {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 2rem;
}

.summary-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.score-badge-big {
  font-size: 3rem;
  font-weight: 800;
  color: var(--color-accent);
}

.level-transition-box {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  background-color: var(--color-bg);
  padding: 1.25rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.level-transition-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.lvl-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-muted);
}

.transition-arrow {
  font-size: 1.5rem;
  color: var(--color-text-light);
}

.results-actions {
  display: flex;
  gap: 1rem;
}

.review-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.5rem;
}

.review-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.review-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.correct-border {
  border-left: 4px solid var(--color-success);
}

.incorrect-border {
  border-left: 4px solid var(--color-danger);
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.review-num {
  font-size: var(--font-size-xs);
  font-weight: 800;
  color: var(--color-text-muted);
}

.review-q-text {
  font-size: var(--font-size-base);
}

.review-options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.review-opt {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.875rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
}

.opt-correct {
  background-color: var(--color-success-light);
  border-color: #a7f3d0;
  font-weight: 600;
}

.opt-chosen-wrong {
  background-color: var(--color-danger-light);
  border-color: #fecaca;
  font-weight: 600;
}

.opt-label {
  font-weight: 700;
  font-size: var(--font-size-xs);
}

.opt-tag {
  margin-left: auto;
  font-size: 0.6875rem;
  font-weight: 700;
  padding: 0.15rem 0.4rem;
  border-radius: var(--radius-sm);
}

.tag-correct { background-color: #d1fae5; color: #065f46; }
.tag-wrong { background-color: #fee2e2; color: #991b1b; }

.explanation-box {
  background-color: var(--color-bg);
  padding: 0.75rem;
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  line-height: 1.5;
}

.citation-box {
  background-color: #f8fafc;
  border-left: 3px solid #64748b;
  padding: 0.625rem 0.875rem;
  font-size: var(--font-size-xs);
}

.citation-label {
  font-weight: 700;
  color: var(--color-text-muted);
  display: block;
  margin-bottom: 0.25rem;
}

.citation-quote {
  font-style: italic;
  color: var(--color-text-main);
}
</style>
