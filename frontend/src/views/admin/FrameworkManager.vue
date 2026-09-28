<template>
  <div class="framework-manager">
    <div class="page-header">
      <div>
        <h1 class="page-title">Competency Framework Manager</h1>
        <p class="page-description">
          Define and maintain official competencies, job roles, required proficiency levels, and prerequisite dependency graphs with DAG cycle detection.
        </p>
      </div>
    </div>

    <!-- Alert / Feedback Banners -->
    <div v-if="successMsg" class="alert alert-success">
      <span>{{ successMsg }}</span>
      <button class="alert-close" @click="successMsg = ''">&times;</button>
    </div>
    <div v-if="cycleError" class="alert alert-cycle">
      <div class="cycle-error-content">
        <span class="cycle-icon">⚠️</span>
        <div>
          <strong class="cycle-title">Circular Dependency / Cycle Rejected:</strong>
          <p class="cycle-text">{{ cycleError }}</p>
          <span class="cycle-hint">
            The competency graph must remain an acyclic directed graph (DAG). Adding this prerequisite would create an infinite learning loop.
          </span>
        </div>
      </div>
      <button class="alert-close" @click="cycleError = ''">&times;</button>
    </div>
    <div v-if="errorMsg" class="alert alert-danger">
      <span>{{ errorMsg }}</span>
      <button class="alert-close" @click="errorMsg = ''">&times;</button>
    </div>

    <!-- Tabbed Navigation -->
    <div class="framework-tabs">
      <button
        class="tab-btn"
        :class="{ active: currentTab === 'competencies' }"
        @click="currentTab = 'competencies'"
      >
        🎯 Competencies ({{ competencies.length }})
      </button>
      <button
        class="tab-btn"
        :class="{ active: currentTab === 'roles' }"
        @click="currentTab = 'roles'"
      >
        💼 Job Roles ({{ roles.length }})
      </button>
      <button
        class="tab-btn"
        :class="{ active: currentTab === 'role_competencies' }"
        @click="currentTab = 'role_competencies'"
      >
        📋 Role Requirements
      </button>
      <button
        class="tab-btn"
        :class="{ active: currentTab === 'prerequisites' }"
        @click="currentTab = 'prerequisites'"
      >
        🔗 Prerequisites (DAG) ({{ prerequisites.length }})
      </button>
    </div>

    <!-- TAB 1: Competencies -->
    <div v-if="currentTab === 'competencies'" class="tab-panel">
      <div class="panel-header">
        <h3>Competency Directory</h3>
        <button class="btn btn-primary btn-sm" @click="openCompetencyModal()">
          + Add New Competency
        </button>
      </div>

      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 70px;">ID</th>
              <th>Name</th>
              <th>Description</th>
              <th style="width: 140px;">Prerequisites</th>
              <th style="width: 150px; text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="comp in competencies" :key="comp.id">
              <td class="text-muted">#{{ comp.id }}</td>
              <td><strong>{{ comp.name }}</strong></td>
              <td class="text-muted text-sm">{{ comp.description || '—' }}</td>
              <td>
                <span v-if="comp.prerequisites && comp.prerequisites.length > 0" class="badge badge-info">
                  {{ comp.prerequisites.length }} required
                </span>
                <span v-else class="text-muted text-xs">None</span>
              </td>
              <td style="text-align: right;">
                <button class="btn btn-secondary btn-xs" @click="openCompetencyModal(comp)">
                  Edit
                </button>
                <button class="btn btn-danger btn-xs" style="margin-left: 0.5rem;" @click="confirmDelete('competency', comp)">
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 2: Roles -->
    <div v-if="currentTab === 'roles'" class="tab-panel">
      <div class="panel-header">
        <h3>Job Roles Directory</h3>
        <button class="btn btn-primary btn-sm" @click="openRoleModal()">
          + Add New Role
        </button>
      </div>

      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 70px;">ID</th>
              <th>Role Title</th>
              <th>Description</th>
              <th style="width: 160px; text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in roles" :key="r.id">
              <td class="text-muted">#{{ r.id }}</td>
              <td><strong>{{ r.name }}</strong></td>
              <td class="text-muted text-sm">{{ r.description || '—' }}</td>
              <td style="text-align: right;">
                <button class="btn btn-secondary btn-xs" @click="openRoleModal(r)">
                  Edit
                </button>
                <button class="btn btn-danger btn-xs" style="margin-left: 0.5rem;" @click="confirmDelete('role', r)">
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 3: Role Competency Requirements -->
    <div v-if="currentTab === 'role_competencies'" class="tab-panel">
      <div class="panel-header role-comp-header">
        <div class="role-selector-wrap">
          <label class="form-label" style="margin-bottom: 0;">Select Role:</label>
          <select v-model="selectedRoleForComp" class="form-control" @change="loadRoleRequirements">
            <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </div>

        <button class="btn btn-primary btn-sm" @click="showAddRoleCompModal = true">
          + Add / Update Requirement
        </button>
      </div>

      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>Competency Name</th>
              <th>Required Proficiency Level</th>
              <th style="width: 120px; text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="roleRequirements.length === 0">
              <td colspan="3" class="text-center text-muted py-6">
                No competencies assigned to this role yet. Click "+ Add / Update Requirement" to assign.
              </td>
            </tr>
            <tr v-for="rc in roleRequirements" :key="rc.competency_id">
              <td><strong>{{ rc.competency_name || getCompetencyName(rc.competency_id) }}</strong></td>
              <td>
                <span class="badge badge-info">Level {{ rc.required_level }} (1 to 5)</span>
              </td>
              <td style="text-align: right;">
                <button class="btn btn-danger btn-xs" @click="removeRoleComp(rc.competency_id)">
                  Remove
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 4: Prerequisites (Dependencies) -->
    <div v-if="currentTab === 'prerequisites'" class="tab-panel">
      <div class="panel-header">
        <div>
          <h3>Prerequisite Dependencies (DAG)</h3>
          <p class="panel-subtitle">Specifies that a learner must acquire Competency B before Competency A.</p>
        </div>
        <button class="btn btn-primary btn-sm" @click="showAddPrereqModal = true">
          + Add Prerequisite Rule
        </button>
      </div>

      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 70px;">ID</th>
              <th>Target Competency</th>
              <th style="width: 50px; text-align: center;">Requires</th>
              <th>Prerequisite Competency</th>
              <th style="width: 120px; text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="prerequisites.length === 0">
              <td colspan="5" class="text-center text-muted py-6">
                No prerequisites configured. All competencies can be learned independently.
              </td>
            </tr>
            <tr v-for="p in prerequisites" :key="p.id">
              <td class="text-muted">#{{ p.id }}</td>
              <td>
                <strong>{{ p.competency_name || getCompetencyName(p.competency_id) }}</strong>
              </td>
              <td style="text-align: center;">&larr;</td>
              <td>
                <span class="badge badge-neutral">
                  {{ p.requires_competency_name || getCompetencyName(p.requires_competency_id) }}
                </span>
              </td>
              <td style="text-align: right;">
                <button class="btn btn-danger btn-xs" @click="deletePrerequisite(p.id)">
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- MODAL: Competency Form -->
    <div v-if="showCompModal" class="modal-backdrop" @click.self="showCompModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>{{ editingComp ? 'Edit Competency' : 'Create New Competency' }}</h3>
          <button class="modal-close" @click="showCompModal = false">&times;</button>
        </div>
        <form @submit.prevent="saveCompetency" class="modal-body">
          <div class="form-group">
            <label class="form-label" for="comp-name">Competency Name</label>
            <input
              id="comp-name"
              v-model="compForm.name"
              type="text"
              class="form-control"
              placeholder="e.g. Advanced Data Wrangling"
              required
            />
          </div>
          <div class="form-group">
            <label class="form-label" for="comp-desc">Description</label>
            <textarea
              id="comp-desc"
              v-model="compForm.description"
              rows="3"
              class="form-control"
              placeholder="Describe the skills and applications covered..."
            ></textarea>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showCompModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="isSaving">
              <span v-if="isSaving">Saving...</span>
              <span v-else>Save Competency</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL: Role Form -->
    <div v-if="showRoleModal" class="modal-backdrop" @click.self="showRoleModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>{{ editingRole ? 'Edit Job Role' : 'Create New Job Role' }}</h3>
          <button class="modal-close" @click="showRoleModal = false">&times;</button>
        </div>
        <form @submit.prevent="saveRole" class="modal-body">
          <div class="form-group">
            <label class="form-label" for="role-name">Role Title</label>
            <input
              id="role-name"
              v-model="roleForm.name"
              type="text"
              class="form-control"
              placeholder="e.g. Senior Statistical Analyst"
              required
            />
          </div>
          <div class="form-group">
            <label class="form-label" for="role-desc">Role Description</label>
            <textarea
              id="role-desc"
              v-model="roleForm.description"
              rows="3"
              class="form-control"
              placeholder="Responsibilities, key statistical duties..."
            ></textarea>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showRoleModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="isSaving">
              <span v-if="isSaving">Saving...</span>
              <span v-else>Save Role</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL: Add Role Competency Requirement -->
    <div v-if="showAddRoleCompModal" class="modal-backdrop" @click.self="showAddRoleCompModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>Set Required Competency Level</h3>
          <button class="modal-close" @click="showAddRoleCompModal = false">&times;</button>
        </div>
        <form @submit.prevent="saveRoleRequirement" class="modal-body">
          <div class="form-group">
            <label class="form-label">Competency</label>
            <select v-model="roleCompForm.competency_id" class="form-control" required>
              <option :value="null" disabled>-- Choose Competency --</option>
              <option v-for="c in competencies" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Required Proficiency Level (1 to 5)</label>
            <select v-model.number="roleCompForm.required_level" class="form-control" required>
              <option :value="1">Level 1 - Novice / Awareness</option>
              <option :value="2">Level 2 - Beginner / Working Knowledge</option>
              <option :value="3">Level 3 - Proficient / Independent Application</option>
              <option :value="4">Level 4 - Advanced / Specialized Practice</option>
              <option :value="5">Level 5 - Expert / Strategic Mastery</option>
            </select>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showAddRoleCompModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="isSaving">
              Save Requirement
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL: Add Prerequisite Rule -->
    <div v-if="showAddPrereqModal" class="modal-backdrop" @click.self="showAddPrereqModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>Add Prerequisite Dependency</h3>
          <button class="modal-close" @click="showAddPrereqModal = false">&times;</button>
        </div>
        <form @submit.prevent="savePrerequisite" class="modal-body">
          <p class="text-sm text-muted">
            Configure a dependency where completing the prerequisite is required before progressing to the target competency.
          </p>

          <div class="form-group">
            <label class="form-label">Target Competency</label>
            <select v-model="prereqForm.competency_id" class="form-control" required>
              <option :value="null" disabled>-- Select Target Competency --</option>
              <option v-for="c in competencies" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Prerequisite Required</label>
            <select v-model="prereqForm.requires_competency_id" class="form-control" required>
              <option :value="null" disabled>-- Select Prerequisite Competency --</option>
              <option v-for="c in competencies" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showAddPrereqModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="isSaving">
              Add Prerequisite
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL: Delete Confirmation -->
    <div v-if="deleteTarget" class="modal-backdrop" @click.self="deleteTarget = null">
      <div class="modal-card">
        <div class="modal-header">
          <h3>Confirm Delete</h3>
          <button class="modal-close" @click="deleteTarget = null">&times;</button>
        </div>
        <div class="modal-body">
          <p>
            Are you sure you want to delete <strong>{{ deleteTarget.item.name }}</strong>?
          </p>
          <p class="text-danger text-sm">
            This action cannot be undone and will remove associated mappings.
          </p>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="deleteTarget = null">Cancel</button>
            <button class="btn btn-danger" :disabled="isSaving" @click="executeDelete">
              Delete Permanently
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'

const currentTab = ref('competencies')

const competencies = ref([])
const roles = ref([])
const prerequisites = ref([])
const roleRequirements = ref([])
const selectedRoleForComp = ref(null)

const successMsg = ref('')
const errorMsg = ref('')
const cycleError = ref('')
const isSaving = ref(false)

// Modals
const showCompModal = ref(false)
const editingComp = ref(null)
const compForm = ref({ name: '', description: '' })

const showRoleModal = ref(false)
const editingRole = ref(null)
const roleForm = ref({ name: '', description: '' })

const showAddRoleCompModal = ref(false)
const roleCompForm = ref({ competency_id: null, required_level: 3 })

const showAddPrereqModal = ref(false)
const prereqForm = ref({ competency_id: null, requires_competency_id: null })

const deleteTarget = ref(null)

const loadAllData = async () => {
  try {
    const [compsRes, rolesRes, prereqsRes] = await Promise.all([
      api.get('/competencies'),
      api.get('/roles'),
      api.get('/prerequisites')
    ])
    competencies.value = compsRes.competencies || []
    roles.value = rolesRes.roles || []
    prerequisites.value = prereqsRes.prerequisites || []

    if (roles.value.length > 0 && !selectedRoleForComp.value) {
      selectedRoleForComp.value = roles.value[0].id
      await loadRoleRequirements()
    }
  } catch (err) {
    errorMsg.value = err.message || 'Failed to load framework data'
  }
}

const loadRoleRequirements = async () => {
  if (!selectedRoleForComp.value) return
  try {
    const res = await api.get(`/roles/${selectedRoleForComp.value}/competencies`)
    roleRequirements.value = res.competencies || []
  } catch (err) {
    errorMsg.value = err.message || 'Failed to load role requirements'
  }
}

onMounted(() => {
  loadAllData()
})

const getCompetencyName = (id) => {
  const c = competencies.value.find((x) => x.id === id)
  return c ? c.name : `Competency #${id}`
}

// Competency Actions
const openCompetencyModal = (comp = null) => {
  editingComp.value = comp
  compForm.value = comp
    ? { name: comp.name, description: comp.description || '' }
    : { name: '', description: '' }
  showCompModal.value = true
}

const saveCompetency = async () => {
  isSaving.value = true
  successMsg.value = ''
  errorMsg.value = ''
  try {
    if (editingComp.value) {
      await api.put(`/competencies/${editingComp.value.id}`, compForm.value)
      successMsg.value = `Competency "${compForm.value.name}" updated successfully.`
    } else {
      await api.post('/competencies', compForm.value)
      successMsg.value = `Competency "${compForm.value.name}" created successfully.`
    }
    showCompModal.value = false
    await loadAllData()
  } catch (err) {
    errorMsg.value = err.message || 'Failed to save competency'
  } finally {
    isSaving.value = false
  }
}

// Role Actions
const openRoleModal = (role = null) => {
  editingRole.value = role
  roleForm.value = role
    ? { name: role.name, description: role.description || '' }
    : { name: '', description: '' }
  showRoleModal.value = true
}

const saveRole = async () => {
  isSaving.value = true
  successMsg.value = ''
  errorMsg.value = ''
  try {
    if (editingRole.value) {
      await api.put(`/roles/${editingRole.value.id}`, roleForm.value)
      successMsg.value = `Role "${roleForm.value.name}" updated successfully.`
    } else {
      await api.post('/roles', roleForm.value)
      successMsg.value = `Role "${roleForm.value.name}" created successfully.`
    }
    showRoleModal.value = false
    await loadAllData()
  } catch (err) {
    errorMsg.value = err.message || 'Failed to save job role'
  } finally {
    isSaving.value = false
  }
}

// Role Requirement Actions
const saveRoleRequirement = async () => {
  if (!selectedRoleForComp.value || !roleCompForm.value.competency_id) return
  isSaving.value = true
  successMsg.value = ''
  errorMsg.value = ''
  try {
    await api.post(`/roles/${selectedRoleForComp.value}/competencies`, {
      competency_id: roleCompForm.value.competency_id,
      required_level: roleCompForm.value.required_level
    })
    successMsg.value = 'Role competency requirement saved successfully.'
    showAddRoleCompModal.value = false
    await loadRoleRequirements()
  } catch (err) {
    errorMsg.value = err.message || 'Failed to save requirement'
  } finally {
    isSaving.value = false
  }
}

const removeRoleComp = async (competencyId) => {
  try {
    await api.delete(`/roles/${selectedRoleForComp.value}/competencies/${competencyId}`)
    successMsg.value = 'Competency requirement removed from role.'
    await loadRoleRequirements()
  } catch (err) {
    errorMsg.value = err.message || 'Failed to remove requirement'
  }
}

// Prerequisite Actions & Cycle Error Handling
const savePrerequisite = async () => {
  isSaving.value = true
  successMsg.value = ''
  errorMsg.value = ''
  cycleError.value = ''

  try {
    await api.post('/prerequisites', {
      competency_id: prereqForm.value.competency_id,
      requires_competency_id: prereqForm.value.requires_competency_id
    })
    successMsg.value = 'Prerequisite dependency registered successfully.'
    showAddPrereqModal.value = false
    prereqForm.value = { competency_id: null, requires_competency_id: null }
    await loadAllData()
  } catch (err) {
    // Check if error is related to cycles or self reference
    const msg = err.message || 'Prerequisite creation failed'
    if (msg.toLowerCase().includes('cycle') || msg.toLowerCase().includes('circular') || msg.toLowerCase().includes('itself')) {
      cycleError.value = msg
    } else {
      errorMsg.value = msg
    }
  } finally {
    isSaving.value = false
  }
}

const deletePrerequisite = async (prereqId) => {
  try {
    await api.delete(`/prerequisites/${prereqId}`)
    successMsg.value = 'Prerequisite dependency removed.'
    await loadAllData()
  } catch (err) {
    errorMsg.value = err.message || 'Failed to remove prerequisite'
  }
}

// Delete Confirmation
const confirmDelete = (type, item) => {
  deleteTarget.value = { type, item }
}

const executeDelete = async () => {
  if (!deleteTarget.value) return
  isSaving.value = true
  const { type, item } = deleteTarget.value

  try {
    if (type === 'competency') {
      await api.delete(`/competencies/${item.id}`)
      successMsg.value = `Competency "${item.name}" deleted successfully.`
    } else if (type === 'role') {
      await api.delete(`/roles/${item.id}`)
      successMsg.value = `Role "${item.name}" deleted successfully.`
    }
    deleteTarget.value = null
    await loadAllData()
  } catch (err) {
    errorMsg.value = err.message || 'Deletion failed'
  } finally {
    isSaving.value = false
  }
}
</script>

<style scoped>
.framework-manager {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

.alert-cycle {
  background-color: #fff7ed;
  border: 2px solid #f97316;
  color: #9a3412;
  padding: 1rem 1.25rem;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.cycle-error-content {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}

.cycle-icon {
  font-size: 1.5rem;
  line-height: 1;
}

.cycle-title {
  font-size: var(--font-size-sm);
  font-weight: 800;
  display: block;
  margin-bottom: 0.25rem;
}

.cycle-text {
  margin: 0.25rem 0;
  font-family: monospace;
  font-size: var(--font-size-xs);
  background: rgba(249, 115, 22, 0.1);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.cycle-hint {
  font-size: var(--font-size-xs);
  color: #c2410c;
  display: block;
}

.alert-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: inherit;
}

/* Tabs */
.framework-tabs {
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.25rem;
  overflow-x: auto;
}

.tab-btn {
  background: none;
  border: none;
  padding: 0.625rem 1rem;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-muted);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.tab-btn:hover {
  color: var(--color-text-main);
  background-color: var(--color-surface-hover);
}

.tab-btn.active {
  color: var(--color-accent);
  border-bottom: 2px solid var(--color-accent);
  background-color: var(--color-surface);
}

/* Tab Panel */
.tab-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.panel-header h3 {
  font-size: var(--font-size-lg);
  font-weight: 700;
  margin: 0;
}

.panel-subtitle {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 0.25rem;
}

.role-comp-header {
  align-items: flex-end;
}

.role-selector-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.btn-xs {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  border-radius: var(--radius-sm);
}

/* Modals */
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
