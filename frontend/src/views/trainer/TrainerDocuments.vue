<template>
  <div class="trainer-documents">
    <div class="page-header">
      <div>
        <h1 class="page-title">Training Documents</h1>
        <p class="page-description">
          Upload reference training materials (PDF, DOCX, TXT) and automatically generate assessment questions using AI.
        </p>
      </div>
      <button class="btn btn-primary" @click="showUploadModal = true">
        <span>+</span> Upload Document
      </button>
    </div>

    <!-- Alert Messages -->
    <div v-if="successMsg" class="alert alert-success">
      <span>{{ successMsg }}</span>
      <button class="alert-close" @click="successMsg = ''">&times;</button>
    </div>
    <div v-if="errorMsg" class="alert alert-danger">
      <span>{{ errorMsg }}</span>
      <button class="alert-close" @click="errorMsg = ''">&times;</button>
    </div>

    <!-- Upload Document Modal -->
    <div v-if="showUploadModal" class="modal-backdrop" @click.self="showUploadModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>Upload Training Document</h3>
          <button class="modal-close" @click="showUploadModal = false">&times;</button>
        </div>

        <form @submit.prevent="handleUpload" class="modal-body">
          <!-- Dropzone -->
          <div
            class="dropzone"
            :class="{ 'is-dragging': isDragging, 'has-file': !!selectedFile }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="triggerFileInput"
          >
            <input
              type="file"
              ref="fileInput"
              class="hidden-input"
              accept=".pdf,.docx,.txt"
              @change="handleFileSelect"
            />
            <div v-if="!selectedFile" class="dropzone-prompt">
              <span class="dropzone-icon">📁</span>
              <p class="dropzone-text"><strong>Click to browse</strong> or drag & drop file here</p>
              <span class="dropzone-hint">Supported formats: PDF, DOCX, TXT (Maximum size: 10 MB)</span>
            </div>
            <div v-else class="dropzone-selected">
              <span class="file-icon">📄</span>
              <div class="file-details">
                <span class="file-name">{{ selectedFile.name }}</span>
                <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
              </div>
              <button type="button" class="btn-remove-file" @click.stop="clearSelectedFile">&times;</button>
            </div>
          </div>

          <div v-if="validationError" class="field-error">
            {{ validationError }}
          </div>

          <div class="form-group">
            <label class="form-label" for="doc-title">Document Title</label>
            <input
              id="doc-title"
              v-model="uploadTitle"
              type="text"
              class="form-control"
              placeholder="e.g. Statistical Analysis Fundamentals"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label" for="doc-comp">Linked Competency</label>
            <select id="doc-comp" v-model="selectedCompetencyId" class="form-control">
              <option :value="null">-- Select Associated Competency (Optional) --</option>
              <option v-for="c in competencies" :key="c.id" :value="c.id">
                {{ c.name }}
              </option>
            </select>
            <span class="form-hint">Links questions generated from this document to a specific competency.</span>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showUploadModal = false">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary" :disabled="!selectedFile || isUploading">
              <span v-if="isUploading">Uploading & Indexing...</span>
              <span v-else>Upload & Index</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Generate Questions Modal -->
    <div v-if="showGenerateModal && activeDocument" class="modal-backdrop" @click.self="closeGenerateModal">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h3>Generate Questions</h3>
            <p class="modal-subtitle">Document: {{ activeDocument.title }}</p>
          </div>
          <button class="modal-close" @click="closeGenerateModal">&times;</button>
        </div>

        <div class="modal-body">
          <div v-if="!isGenerating && !generationResult">
            <div class="form-group">
              <label class="form-label">Number of Questions</label>
              <div class="range-row">
                <input
                  v-model.number="genForm.num_questions"
                  type="range"
                  min="1"
                  max="15"
                  class="range-slider"
                />
                <span class="range-val">{{ genForm.num_questions }}</span>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">Target Difficulty</label>
              <select v-model="genForm.difficulty" class="form-control">
                <option value="easy">Easy (Foundational Recall)</option>
                <option value="medium">Medium (Application & Understanding)</option>
                <option value="hard">Hard (Analysis & Complex Scenarios)</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Topic / Keyword Focus (Optional)</label>
              <input
                v-model="genForm.topic_focus"
                type="text"
                class="form-control"
                placeholder="e.g. Sampling distribution, hypothesis testing"
              />
              <span class="form-hint">Guides the semantic chunk retrieval to focus on specific topics.</span>
            </div>

            <div class="modal-footer">
              <button class="btn btn-secondary" @click="closeGenerateModal">Cancel</button>
              <button class="btn btn-primary" @click="startGeneration">
                Generate Questions
              </button>
            </div>
          </div>

          <!-- Loading State -->
          <div v-else-if="isGenerating" class="generating-state">
            <div class="spinner"></div>
            <h4>Synthesizing Questions with Gemini AI...</h4>
            <p class="text-muted">
              Retrieving document chunks, generating multiple-choice questions, and running automated quality validation checks.
            </p>
          </div>

          <!-- Result State -->
          <div v-else-if="generationResult" class="generation-result">
            <div class="result-badge success">
              ✨ Generation Complete
            </div>

            <div class="result-stats">
              <div class="stat-box">
                <span class="stat-number">{{ generationResult.generated || 0 }}</span>
                <span class="stat-label">Generated</span>
              </div>
              <div class="stat-box kept">
                <span class="stat-number">{{ generationResult.kept || 0 }}</span>
                <span class="stat-label">Kept (Draft)</span>
              </div>
              <div class="stat-box rejected">
                <span class="stat-number">{{ generationResult.rejected || 0 }}</span>
                <span class="stat-label">Filtered</span>
              </div>
            </div>

            <div v-if="generationResult.rejected_reasons && generationResult.rejected_reasons.length > 0" class="rejection-reasons">
              <h5 class="rejection-title">Quality Filter Reasons:</h5>
              <ul>
                <li v-for="(reason, idx) in generationResult.rejected_reasons" :key="idx">
                  {{ reason }}
                </li>
              </ul>
            </div>

            <div class="modal-footer">
              <button class="btn btn-secondary" @click="closeGenerateModal">Close</button>
              <router-link
                :to="{ path: '/trainer/review', query: { document_id: activeDocument.id, status: 'draft' } }"
                class="btn btn-primary"
              >
                Review New Questions &rarr;
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Documents List -->
    <LoadingState v-if="isLoading" message="Loading documents..." />
    <ErrorState v-else-if="fetchError" :message="fetchError" :retry="loadData" />

    <div v-else>
      <EmptyState
        v-if="documents.length === 0"
        title="No documents uploaded yet"
        description="Upload training documents to index their knowledge and generate assessment MCQs."
        action-label="+ Upload First Document"
        @action="showUploadModal = true"
      />

      <div v-else class="documents-grid">
        <div v-for="doc in documents" :key="doc.id" class="doc-card">
          <div class="doc-card-header">
            <div class="doc-badge-row">
              <span class="badge badge-info">{{ doc.file_extension || getFileExt(doc.filename) }}</span>
              <span v-if="doc.competency_name || getCompetencyName(doc.competency_id)" class="badge badge-neutral">
                🎯 {{ doc.competency_name || getCompetencyName(doc.competency_id) }}
              </span>
            </div>
            <span class="doc-date">{{ formatDate(doc.created_at) }}</span>
          </div>

          <h3 class="doc-title">{{ doc.title }}</h3>
          <p class="doc-filename">{{ doc.filename }}</p>

          <!-- Question Status Counters -->
          <div class="status-counts">
            <div class="status-pill status-draft" title="Questions pending trainer review">
              <span class="pill-dot"></span>
              <span class="pill-label">Draft:</span>
              <strong>{{ doc.draft_count || 0 }}</strong>
            </div>
            <div class="status-pill status-approved" title="Approved questions ready for assessments">
              <span class="pill-dot"></span>
              <span class="pill-label">Approved:</span>
              <strong>{{ doc.approved_count || 0 }}</strong>
            </div>
            <div class="status-pill status-rejected" title="Rejected questions">
              <span class="pill-dot"></span>
              <span class="pill-label">Rejected:</span>
              <strong>{{ doc.rejected_count || 0 }}</strong>
            </div>
          </div>

          <div class="doc-footer">
            <button class="btn btn-secondary btn-sm" @click="openGenerateModal(doc)">
              ✨ Generate MCQs
            </button>
            <router-link
              :to="{ path: '/trainer/review', query: { document_id: doc.id } }"
              class="btn btn-primary btn-sm"
            >
              Review Questions ({{ doc.questions_count || 0 }})
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const documents = ref([])
const competencies = ref([])
const isLoading = ref(true)
const fetchError = ref(null)

// Upload state
const showUploadModal = ref(false)
const selectedFile = ref(null)
const uploadTitle = ref('')
const selectedCompetencyId = ref(null)
const isDragging = ref(false)
const isUploading = ref(false)
const validationError = ref('')
const fileInput = ref(null)

// Generation state
const showGenerateModal = ref(false)
const activeDocument = ref(null)
const isGenerating = ref(false)
const generationResult = ref(null)
const genForm = ref({
  num_questions: 5,
  difficulty: 'medium',
  topic_focus: ''
})

// Notification
const successMsg = ref('')
const errorMsg = ref('')

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt']
const MAX_SIZE_BYTES = 10 * 1024 * 1024 // 10MB

const loadData = async () => {
  isLoading.value = true
  fetchError.value = null
  try {
    const [docsRes, compsRes] = await Promise.all([
      api.get('/documents'),
      api.get('/competencies')
    ])
    documents.value = docsRes.documents || []
    competencies.value = compsRes.competencies || []
  } catch (err) {
    fetchError.value = err.message || 'Failed to load documents'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadData()
})

const getCompetencyName = (id) => {
  if (!id) return null
  const c = competencies.value.find((item) => item.id === id)
  return c ? c.name : null
}

const getFileExt = (filename) => {
  if (!filename) return 'DOC'
  const parts = filename.split('.')
  return parts.length > 1 ? parts.pop().toUpperCase() : 'DOC'
}

const formatDate = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

// File dropzone handlers
const triggerFileInput = () => {
  if (fileInput.value) fileInput.value.click()
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  validateAndSetFile(file)
}

const handleDrop = (e) => {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  validateAndSetFile(file)
}

const validateAndSetFile = (file) => {
  validationError.value = ''
  if (!file) return

  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    validationError.value = `Invalid file format (${ext}). Only PDF, DOCX, and TXT files are accepted.`
    return
  }

  if (file.size > MAX_SIZE_BYTES) {
    validationError.value = `File exceeds the 10 MB limit (${formatFileSize(file.size)}).`
    return
  }

  selectedFile.value = file
  if (!uploadTitle.value) {
    // Default title to base filename
    const base = file.name.substring(0, file.name.lastIndexOf('.')) || file.name
    uploadTitle.value = base.replace(/[-_]/g, ' ')
  }
}

const clearSelectedFile = () => {
  selectedFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

const handleUpload = async () => {
  if (!selectedFile.value) return
  isUploading.value = true
  validationError.value = ''

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('title', uploadTitle.value.trim())
    if (selectedCompetencyId.value) {
      formData.append('competency_id', selectedCompetencyId.value)
    }

    const res = await api.post('/documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    successMsg.value = `Document "${res.document.title}" uploaded and indexed into ${res.chunks_count} chunks.`
    showUploadModal.value = false
    clearSelectedFile()
    uploadTitle.value = ''
    selectedCompetencyId.value = null
    await loadData()
  } catch (err) {
    validationError.value = err.message || 'Upload failed'
  } finally {
    isUploading.value = false
  }
}

// Question Generation
const openGenerateModal = (doc) => {
  activeDocument.value = doc
  generationResult.value = null
  genForm.value = {
    num_questions: 5,
    difficulty: 'medium',
    topic_focus: ''
  }
  showGenerateModal.value = true
}

const closeGenerateModal = () => {
  showGenerateModal.value = false
  activeDocument.value = null
  generationResult.value = null
}

const startGeneration = async () => {
  if (!activeDocument.value) return
  isGenerating.value = true
  errorMsg.value = ''

  try {
    const res = await api.post(`/documents/${activeDocument.value.id}/generate`, {
      num_questions: genForm.value.num_questions,
      difficulty: genForm.value.difficulty,
      topic_focus: genForm.value.topic_focus ? genForm.value.topic_focus.trim() : null
    })
    generationResult.value = res.result
    await loadData() // refresh document counts
  } catch (err) {
    errorMsg.value = err.message || 'Generation failed'
    closeGenerateModal()
  } finally {
    isGenerating.value = false
  }
}
</script>

<style scoped>
.trainer-documents {
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
  background-color: var(--color-success-light);
  color: var(--color-success-text);
  border: 1px solid var(--color-success-border);
}

.alert-danger {
  background-color: var(--color-danger-light);
  color: var(--color-danger-text);
  border: 1px solid var(--color-danger-border);
}

.alert-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: inherit;
}

/* Grid & Cards */
.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1.25rem;
}

.doc-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.doc-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.doc-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.doc-badge-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.doc-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-light);
}

.doc-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text-main);
  margin-bottom: 0.25rem;
}

.doc-filename {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-family: monospace;
  margin-bottom: 1rem;
  word-break: break-all;
}

/* Status Counts */
.status-counts {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
  padding: 0.625rem;
  background-color: var(--color-bg);
  border-radius: var(--radius-md);
}

.status-pill {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: var(--font-size-xs);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.pill-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-draft .pill-dot { background-color: var(--color-warning); }
.status-approved .pill-dot { background-color: var(--color-success); }
.status-rejected .pill-dot { background-color: var(--color-danger); }

.doc-footer {
  margin-top: auto;
  display: flex;
  gap: 0.5rem;
}

/* Modals */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(2px);
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
  max-width: 540px;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.modal-header h3 {
  font-size: var(--font-size-lg);
  font-weight: 700;
}

.modal-subtitle {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 0.25rem;
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
  gap: 1.25rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1rem;
}

/* Dropzone */
.dropzone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  padding: 2rem 1rem;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  background-color: var(--color-bg);
}

.dropzone:hover, .dropzone.is-dragging {
  border-color: var(--color-accent);
  background-color: var(--color-accent-light);
}

.dropzone.has-file {
  border-style: solid;
  border-color: var(--color-accent);
  background-color: var(--color-surface);
}

.hidden-input {
  display: none;
}

.dropzone-icon {
  font-size: 2.25rem;
  display: block;
  margin-bottom: 0.5rem;
}

.dropzone-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-main);
  margin-bottom: 0.25rem;
}

.dropzone-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-light);
}

.dropzone-selected {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-align: left;
}

.file-icon {
  font-size: 1.75rem;
}

.file-details {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.file-name {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-main);
}

.file-size {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.btn-remove-file {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--color-text-muted);
  cursor: pointer;
}

.field-error {
  font-size: var(--font-size-xs);
  color: var(--color-danger);
  font-weight: 500;
}

/* Generation elements */
.range-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.range-slider {
  flex: 1;
  accent-color: var(--color-accent);
}

.range-val {
  font-weight: 700;
  font-size: var(--font-size-base);
  width: 2rem;
  text-align: center;
}

.generating-state {
  text-align: center;
  padding: 2.5rem 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.spinner {
  width: 44px;
  height: 44px;
  border: 4px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.generation-result {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.result-badge {
  text-align: center;
  font-weight: 700;
  font-size: var(--font-size-base);
  color: var(--color-success-text);
}

.result-stats {
  display: flex;
  gap: 1rem;
}

.stat-box {
  flex: 1;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1rem;
  text-align: center;
  display: flex;
  flex-direction: column;
}

.stat-box.kept {
  border-color: var(--color-success-border);
  background-color: var(--color-success-light);
  color: var(--color-success-text);
}

.stat-box.rejected {
  border-color: var(--color-danger-border);
  background-color: var(--color-danger-light);
  color: var(--color-danger-text);
}

.stat-number {
  font-size: var(--font-size-xl);
  font-weight: 800;
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.rejection-reasons {
  background: var(--color-bg);
  border-radius: var(--radius-md);
  padding: 1rem;
  font-size: var(--font-size-xs);
}

.rejection-title {
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--color-danger);
}

.rejection-reasons ul {
  padding-left: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
</style>
