<template>
  <div class="auth-page">
    <div class="auth-card card">
      <div class="auth-top-bar">
        <ThemeToggle />
      </div>
      <div class="auth-header">
        <div class="auth-logo">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <h2>{{ isRegistering ? 'Create your Account' : 'Welcome back' }}</h2>
        <p>{{ isRegistering ? 'Start your skill journey with MoSPI' : 'Sign in to access your learning portal' }}</p>
      </div>

      <!-- Error alert -->
      <div v-if="errorMessage" class="error-banner">
        <span>{{ errorMessage }}</span>
      </div>

      <form @submit.prevent="handleSubmit" class="auth-form">
        <div v-if="isRegistering" class="form-group">
          <label class="form-label" for="reg-name">Full Name</label>
          <input
            id="reg-name"
            v-model="form.name"
            type="text"
            class="form-control"
            placeholder="e.g. Aditi Purohit"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="auth-email">Email Address</label>
          <input
            id="auth-email"
            v-model="form.email"
            type="email"
            class="form-control"
            placeholder="name@example.com"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="auth-password">Password</label>
          <input
            id="auth-password"
            v-model="form.password"
            type="password"
            class="form-control"
            placeholder="At least 6 characters"
            required
          />
        </div>

        <div v-if="isRegistering" class="form-group">
          <label class="form-label" for="reg-role">Role</label>
          <select id="reg-role" v-model="form.role" class="form-control">
            <option value="learner">Learner (Statistical Staff)</option>
            <option value="trainer">Trainer (Course & Assessment Author)</option>
            <option value="admin">Administrator</option>
          </select>
        </div>

        <button type="submit" class="btn btn-primary btn-lg submit-btn" :disabled="auth.isLoading">
          <span v-if="auth.isLoading">Processing...</span>
          <span v-else>{{ isRegistering ? 'Register Account' : 'Sign In' }}</span>
        </button>
      </form>

      <div class="auth-toggle">
        <span v-if="!isRegistering">Don't have an account? </span>
        <span v-else>Already have an account? </span>
        <button type="button" class="btn-link" @click="toggleMode">
          {{ isRegistering ? 'Sign In' : 'Register' }}
        </button>
      </div>

      <div class="demo-credentials">
        <strong>Demo Accounts (seeded):</strong>
        <div>Learner: <code>learner1@example.com</code> / <code>learner123</code></div>
        <div>Trainer: <code>trainer@example.com</code> / <code>trainer123</code></div>
        <div>Admin: <code>admin@example.com</code> / <code>admin123</code></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ThemeToggle from '@/components/common/ThemeToggle.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const isRegistering = ref(route.path === '/register')
const errorMessage = ref('')

watch(() => route.path, (newPath) => {
  isRegistering.value = newPath === '/register'
})

const form = reactive({
  name: '',
  email: '',
  password: '',
  role: 'learner'
})

const toggleMode = () => {
  isRegistering.value = !isRegistering.value
  errorMessage.value = ''
  if (isRegistering.value) {
    router.replace('/register')
  } else {
    router.replace('/login')
  }
}

const handleSubmit = async () => {
  errorMessage.value = ''
  try {
    if (isRegistering.value) {
      await auth.register(form.name, form.email, form.password, form.role)
    } else {
      await auth.login(form.email, form.password)
    }
    router.push('/dashboard')
  } catch (err) {
    errorMessage.value = err.message || 'Authentication failed'
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: linear-gradient(135deg, var(--color-bg) 0%, var(--color-surface-hover) 100%);
}

.auth-card {
  width: 100%;
  max-width: 440px;
  padding: 2.5rem 2rem;
  position: relative;
}

.auth-top-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.5rem;
}

.auth-header {
  text-align: center;
  margin-bottom: 2rem;
}

.auth-logo {
  color: var(--color-accent);
  display: inline-flex;
  margin-bottom: 0.75rem;
}

.auth-header h2 {
  font-size: var(--font-size-2xl);
  margin-bottom: 0.35rem;
}

.auth-header p {
  font-size: var(--font-size-sm);
}

.error-banner {
  background-color: var(--color-danger-light);
  color: var(--color-danger-text);
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  margin-bottom: 1.25rem;
  font-size: var(--font-size-sm);
  border: 1px solid var(--color-danger-border);
}

.submit-btn {
  width: 100%;
  margin-top: 0.5rem;
}

.auth-toggle {
  text-align: center;
  margin-top: 1.5rem;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.btn-link {
  background: none;
  border: none;
  color: var(--color-accent);
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  font-size: inherit;
}

.btn-link:hover {
  text-decoration: underline;
}

.demo-credentials {
  margin-top: 2rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--color-border);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  line-height: 1.6;
}

.demo-credentials code {
  background: var(--color-bg);
  padding: 0.1rem 0.3rem;
  border-radius: var(--radius-sm);
  font-weight: 600;
  color: var(--color-text-main);
}
</style>
