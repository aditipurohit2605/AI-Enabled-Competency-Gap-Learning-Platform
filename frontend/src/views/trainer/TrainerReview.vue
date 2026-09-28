<template>
  <div class="trainer-review">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Review Assessment Questions</h1>
        <p class="page-description">
          Inspect, refine, approve, or reject multiple-choice questions generated from training materials before they are served to learners.
        </p>
      </div>

      <div class="header-actions">
        <button
          v-if="draftQuestionsCount > 0"
          class="btn btn-primary"
          @click="showApproveAllConfirm = true"
        >
          ✓ Approve All Draft Questions ({{ draftQuestionsCount }})
        </button>
      </div>
    </div>

    <!-- Feedback messages -->
    <div v-if="successMsg" class="alert alert-success">
      <span>{{ successMsg }}</span>
      <button class="alert-close" @click="successMsg = ''">&times;</button>
    </div>
    <div v-if="errorMsg" class="alert alert-danger">
      <span>{{ errorMsg }}</span>
      <button class="alert-close" @click="errorMsg = ''">&times;</button>
    </div>

    <!-- Filter Toolbar -->
    <div class="filters-bar">
      <div class="filter-group">
        <label class="filter-label">Filter by Document:</label>
        <select v-model="selectedDocId" class="form-control filter-select" @change="applyFilters">
          <option value="">All Documents</option>
          <option v-for="d in documents" :key="d.id" :value="d.id">
            {{ d.title }}
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">Status Filter:</label>
        <div class="status-tab-group">
          <button
            class="status-tab"
            :class="{ active: currentStatus === 'all' }"
            @click="setStatusFilter('all')"
          >
            All ({{ allCount }})
          </button>
          <button
            class="status-tab draft"
            :class="{ active: currentStatus === 'draft' }"
            @click="setStatusFilter('draft')"
          >
            Draft ({{ draftCount }})
          </button>
          <button
            class="status-tab approved"
            :class="{ active: currentStatus === 'approved' }"
            @click="setStatusFilter('approved')"
          >
            Approved ({{ approvedCount }})
          </button>
          <button
            class="status-tab rejected"
            :class="{ active: currentStatus === 'rejected' }"
            @click="setStatusFilter('rejected')"
          >
            Rejected ({{ rejectedCount }})
          </button>
        </div>
      </div>
    </div>

    <!-- Confirmation Modal for Approve All -->
    <div v-if="showApproveAllConfirm" class="modal-backdrop" @click.self="showApproveAllConfirm = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>Confirm Bulk Approval</h3>
          <button class="modal-close" @click="showApproveAllConfirm = false">&times;</button>
        </div>
        <div class="modal-body">
          <p>
            Are you sure you want to approve <strong>{{ draftQuestionsCount }}</strong> draft question(s)?
          </p>
          <p class="text-muted">
            Once approved, these questions will immediately enter the active question pool and be eligible for learner assessments.
          </p>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showApproveAllConfirm = false">
              Cancel
            </button>
            <button class="btn btn-primary" :disabled="isApprovingAll" @click="handleApproveAll">
              <span v-if="isApprovingAll">Approving...</span>
              <span v-else>Yes, Approve All</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Questions List -->
    <LoadingState v-if="isLoading" message="Loading questions..." />
    <ErrorState v-else-if="fetchError" :message="fetchError" :retry="loadData" />

    <div v-else>
      <EmptyState
        v-if="filteredQuestions.length === 0"
        title="No questions match the selected filter"
        description="Try changing the status or document filter, or generate new questions from uploaded documents."
      />

      <div v-else class="questions-list">
        <div
          v-for="q in filteredQuestions"
          :key="q.id"
          class="question-card"
          :class="'card-status-' + q.status"
        >
          <!-- Card Header -->
          <div class="q-header">
            <div class="q-meta-left">
              <span class="q-id">#{{ q.id }}</span>
              <span class="badge" :class="getStatusBadgeClass(q.status)">
                {{ q.status.toUpperCase() }}
              </span>
              <span v-if="q.document_title" class="q-doc-title">
                📄 {{ q.document_title }}
              </span>
            </div>

            <div class="q-meta-right">
              <label class="diff-label">Difficulty:</label>
              <select v-model="q._editDifficulty" class="diff-select form-control">
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          <!-- Question Prompt (Editable) -->
          <div class="form-group">
            <label class="field-label">Question Text</label>
            <textarea
              v-model="q._editText"
              rows="3"
              class="form-control question-textarea"
              placeholder="Question prompt..."
            ></textarea>
          </div>

          <!-- Four Choices (Editable with radio selector for correct answer) -->
          <div class="form-group">
            <label class="field-label">Options (select radio for correct answer)</label>
            <div class="options-container">
              <div
                v-for="(opt, optIdx) in q._editOptions"
                :key="optIdx"
                class="option-row"
                :class="{ 'is-correct': q._editCorrectIndex === optIdx }"
              >
                <label class="radio-label">
                  <input
                    type="radio"
                    :name="'correct_' + q.id"
                    :value="optIdx"
                    v-model="q._editCorrectIndex"
                  />
                  <span class="opt-letter">{{ ['A', 'B', 'C', 'D'][optIdx] }}</span>
                </label>
                <input
                  v-model="q._editOptions[optIdx]"
                  type="text"
                  class="form-control opt-input"
                  placeholder="Option text..."
                />
              </div>
            </div>
          </div>

          <!-- Explanation (Editable) -->
          <div class="form-group">
            <label class="field-label">Explanation</label>
            <textarea
              v-model="q._editExplanation"
              rows="2"
              class="form-control explanation-textarea"
              placeholder="Rationale explaining why the correct choice is right and distractors are wrong..."
            ></textarea>
          </div>

          <!-- Read-only Source Passage Citation -->
          <div v-if="q.source_passage" class="source-passage-box">
            <div class="source-header">
              <span class="source-icon">📖</span>
              <span class="source-label">Source Document Citation (Read-Only)</span>
            </div>
            <blockquote class="source-text">
              "{{ q.source_passage }}"
            </blockquote>
          </div>

          <!-- Per-Question Action Buttons -->
          <div class="q-actions-bar">
            <button
              class="btn btn-secondary btn-sm"
              :disabled="q._isSaving"
              @click="saveQuestion(q)"
            >
              <span v-if="q._isSaving">Saving...</span>
              <span v-else>💾 Save Edits</span>
            </button>

            <div class="q-status-actions">
              <button
                v-if="q.status !== 'approved'"
                class="btn btn-success btn-sm"
                :disabled="q._isUpdating"
                @click="updateStatus(q, 'approved')"
              >
                ✓ Approve
              </button>
              <button
                v-if="q.status !== 'rejected'"
                class="btn btn-danger btn-sm"
                :disabled="q._isUpdating"
                @click="updateStatus(q, 'rejected')"
              >
                ✕ Reject
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const route = useRoute()

const documents = ref([])
const questions = ref([])
const isLoading = ref(true)
const fetchError = ref(null)

const selectedDocId = ref(route.query.document_id ? String(route.query.document_id) : '')
const currentStatus = ref(route.query.status ? String(route.query.status) : 'all')

const successMsg = ref('')
const errorMsg = ref('')
const showApproveAllConfirm = ref(false)
const isApprovingAll = ref(false)

const loadData = async () => {
  isLoading.value = true
  fetchError.value = null
  try {
    const docsRes = await api.get('/documents')
    documents.value = docsRes.documents || []

    const qParams = {}
    if (selectedDocId.value) qParams.document_id = selectedDocId.value
    const qRes = await api.get('/questions', { params: qParams })
    
    const docsMap = {}
    documents.value.forEach((d) => {
      docsMap[d.id] = d.title
    })

    questions.value = (qRes.questions || []).map((q) => ({
      ...q,
      document_title: docsMap[q.document_id] || (q.document ? q.document.title : `Doc #${q.document_id}`),
      _editText: q.text,
      _editOptions: [...(q.options || ['', '', '', ''])],
      _editCorrectIndex: q.correct_index ?? 0,
      _editExplanation: q.explanation || '',
      _editDifficulty: q.difficulty || 'medium',
      _isSaving: false,
      _isUpdating: false
    }))
  } catch (err) {
    fetchError.value = err.message || 'Failed to load questions'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadData()
})

const applyFilters = () => {
  loadData()
}

const setStatusFilter = (status) => {
  currentStatus.value = status
}

// Counts for status tabs
const allCount = computed(() => questions.value.length)
const draftCount = computed(() => questions.value.filter((q) => q.status === 'draft').length)
const approvedCount = computed(() => questions.value.filter((q) => q.status === 'approved').length)
const rejectedCount = computed(() => questions.value.filter((q) => q.status === 'rejected').length)

const draftQuestionsCount = computed(() => {
  return filteredQuestions.value.filter((q) => q.status === 'draft').length
})

const filteredQuestions = computed(() => {
  return questions.value.filter((q) => {
    if (currentStatus.value !== 'all' && q.status !== currentStatus.value) {
      return false
    }
    return true
  })
})

const getStatusBadgeClass = (status) => {
  if (status === 'approved') return 'badge-success'
  if (status === 'rejected') return 'badge-danger'
  return 'badge-warning'
}

// Save edits to question
const saveQuestion = async (q) => {
  q._isSaving = true
  successMsg.value = ''
  errorMsg.value = ''
  try {
    const payload = {
      text: q._editText,
      options: q._editOptions,
      correct_index: q._editCorrectIndex,
      explanation: q._editExplanation,
      difficulty: q._editDifficulty
    }
    const res = await api.put(`/questions/${q.id}`, payload)
    q.text = res.question.text
    q.options = res.question.options
    q.correct_index = res.question.correct_index
    q.explanation = res.question.explanation
    q.difficulty = res.question.difficulty
    successMsg.value = `Question #${q.id} updated successfully.`
  } catch (err) {
    errorMsg.value = err.message || `Failed to update question #${q.id}`
  } finally {
    q._isSaving = false
  }
}

// Approve or Reject question
const updateStatus = async (q, targetStatus) => {
  q._isUpdating = true
  successMsg.value = ''
  errorMsg.value = ''
  try {
    const endpoint = targetStatus === 'approved' ? `/questions/${q.id}/approve` : `/questions/${q.id}/reject`
    const res = await api.post(endpoint)
    q.status = res.question.status
    successMsg.value = `Question #${q.id} marked as ${targetStatus}.`
  } catch (err) {
    errorMsg.value = err.message || `Failed to update status for question #${q.id}`
  } finally {
    q._isUpdating = false
  }
}

// Approve all draft questions
const handleApproveAll = async () => {
  isApprovingAll.value = true
  successMsg.value = ''
  errorMsg.value = ''

  try {
    if (selectedDocId.value) {
      // Use document endpoint if filtered by document
      await api.post(`/documents/${selectedDocId.value}/approve-all`)
    } else {
      // Approve all draft questions currently in list
      const draftList = filteredQuestions.value.filter((q) => q.status === 'draft')
      await Promise.all(draftList.map((q) => api.post(`/questions/${q.id}/approve`)))
    }

    successMsg.value = `All draft questions approved successfully.`
    showApproveAllConfirm.value = false
    await loadData()
  } catch (err) {
    errorMsg.value = err.message || 'Failed to approve questions'
  } finally {
    isApprovingAll.value = false
  }
}
</script>

<style scoped>
.trainer-review {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

/* Alert styles */
.alert {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-success {
  background-color: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.alert-danger {
  background-color: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.alert-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: inherit;
}

/* Filter bar */
.filters-bar {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.filter-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.filter-select {
  min-width: 200px;
}

.status-tab-group {
  display: flex;
  background-color: var(--color-bg);
  padding: 0.25rem;
  border-radius: var(--radius-md);
  gap: 0.25rem;
}

.status-tab {
  background: none;
  border: none;
  padding: 0.375rem 0.75rem;
  font-size: var(--font-size-xs);
  font-weight: 600;
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.status-tab:hover {
  color: var(--color-text-main);
}

.status-tab.active {
  background: var(--color-surface);
  color: var(--color-text-main);
  box-shadow: var(--shadow-sm);
}

.status-tab.draft.active { color: #d97706; }
.status-tab.approved.active { color: #059669; }
.status-tab.rejected.active { color: #dc2626; }

/* Question Cards */
.questions-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.question-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  position: relative;
  transition: border-color var(--transition-fast);
}

.card-status-draft {
  border-left: 4px solid var(--color-warning);
}

.card-status-approved {
  border-left: 4px solid var(--color-success);
}

.card-status-rejected {
  border-left: 4px solid var(--color-danger);
  opacity: 0.85;
}

.q-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.q-meta-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.q-id {
  font-family: monospace;
  font-weight: 700;
  color: var(--color-text-muted);
}

.q-doc-title {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.q-meta-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.diff-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: 600;
}

.diff-select {
  padding: 0.25rem 0.5rem;
  font-size: var(--font-size-xs);
  height: 32px;
}

.field-label {
  display: block;
  font-size: var(--font-size-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-light);
  margin-bottom: 0.375rem;
}

.question-textarea, .explanation-textarea {
  width: 100%;
  font-family: inherit;
  font-size: var(--font-size-sm);
  line-height: 1.5;
  resize: vertical;
}

/* Options */
.options-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 0.5rem 0.75rem;
  transition: all var(--transition-fast);
}

.option-row.is-correct {
  border-color: #10b981;
  background-color: #ecfdf5;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.opt-letter {
  font-weight: 700;
  font-size: var(--font-size-sm);
  color: var(--color-text-main);
  width: 1rem;
}

.opt-input {
  flex: 1;
  background: var(--color-surface);
  font-size: var(--font-size-sm);
}

/* Source passage */
.source-passage-box {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-md);
  padding: 0.875rem 1rem;
}

.source-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.375rem;
}

.source-icon {
  font-size: 1rem;
}

.source-label {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.source-text {
  margin: 0;
  font-size: var(--font-size-xs);
  color: #334155;
  line-height: 1.5;
  font-style: italic;
}

/* Action bar */
.q-actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
}

.q-status-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-success {
  background-color: #10b981;
  color: white;
  border: 1px solid #059669;
}
.btn-success:hover {
  background-color: #059669;
}

.btn-danger {
  background-color: #ef4444;
  color: white;
  border: 1px solid #dc2626;
}
.btn-danger:hover {
  background-color: #dc2626;
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 1rem;
}

.modal-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 480px;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.modal-header {
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--color-text-muted);
}

.modal-body {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1rem;
}
</style>
