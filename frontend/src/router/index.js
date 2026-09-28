import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppShell from '@/components/layout/AppShell.vue'
import LoginView from '@/views/LoginView.vue'
import LearnerDashboard from '@/views/LearnerDashboard.vue'
import MyProfile from '@/views/MyProfile.vue'
import GapReport from '@/views/GapReport.vue'
import LearningPath from '@/views/LearningPath.vue'
import QuizView from '@/views/QuizView.vue'
import HistoryView from '@/views/HistoryView.vue'

// Step 7B Trainer & Admin Views
import TrainerDocuments from '@/views/trainer/TrainerDocuments.vue'
import TrainerReview from '@/views/trainer/TrainerReview.vue'
import AdminAnalytics from '@/views/admin/AdminAnalytics.vue'
import FrameworkManager from '@/views/admin/FrameworkManager.vue'
import AdminUsers from '@/views/admin/AdminUsers.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { guestOnly: true, title: 'Login' }
  },
  {
    path: '/register',
    name: 'register',
    component: LoginView,
    meta: { guestOnly: true, title: 'Register' }
  },
  {
    path: '/',
    component: AppShell,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      // Learner Portal Routes
      {
        path: 'dashboard',
        name: 'dashboard',
        component: LearnerDashboard,
        meta: { requiresAuth: true, title: 'Learner Dashboard' }
      },
      {
        path: 'profile',
        name: 'profile',
        component: MyProfile,
        meta: { requiresAuth: true, title: 'My Profile & Skills' }
      },
      {
        path: 'gap',
        name: 'gap',
        component: GapReport,
        meta: { requiresAuth: true, title: 'Role Gap Analysis' }
      },
      {
        path: 'path',
        name: 'path',
        component: LearningPath,
        meta: { requiresAuth: true, title: 'Learning Curriculum' }
      },
      {
        path: 'quiz',
        name: 'quiz',
        component: QuizView,
        meta: { requiresAuth: true, title: 'Assessments' }
      },
      {
        path: 'history',
        name: 'history',
        component: HistoryView,
        meta: { requiresAuth: true, title: 'Evaluation History' }
      },

      // Trainer Portal Routes (trainer and admin roles)
      {
        path: 'trainer/documents',
        name: 'trainer-documents',
        component: TrainerDocuments,
        meta: { requiresAuth: true, roles: ['trainer', 'admin'], title: 'Training Documents' }
      },
      {
        path: 'trainer/review',
        name: 'trainer-review',
        component: TrainerReview,
        meta: { requiresAuth: true, roles: ['trainer', 'admin'], title: 'Question Review' }
      },

      // Admin Portal Routes (admin role only)
      {
        path: 'admin/analytics',
        name: 'admin-analytics',
        component: AdminAnalytics,
        meta: { requiresAuth: true, roles: ['admin'], title: 'Executive Analytics & Heatmap' }
      },
      {
        path: 'admin/framework',
        name: 'admin-framework',
        component: FrameworkManager,
        meta: { requiresAuth: true, roles: ['admin'], title: 'Framework Manager' }
      },
      {
        path: 'admin/users',
        name: 'admin-users',
        component: AdminUsers,
        meta: { requiresAuth: true, roles: ['admin'], title: 'User Directory' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation Guard for Authentication and Role Authorization
router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  // If token exists in localStorage but user not yet fetched, populate user
  if (auth.token && !auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      // Handled by fetchMe (logs out if invalid)
    }
  }

  const isAuth = auth.isAuthenticated

  if (to.meta.requiresAuth && !isAuth) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  if (to.meta.guestOnly && isAuth) {
    return next({ path: '/dashboard' })
  }

  // Check role restrictions if route specifies allowed roles
  if (to.meta.roles && Array.isArray(to.meta.roles)) {
    if (!to.meta.roles.includes(auth.role)) {
      return next({ path: '/dashboard' })
    }
  }

  next()
})

// Dynamic document title update
router.afterEach((to) => {
  const baseTitle = 'Karmayogi Platform | MoSPI'
  if (to.meta && to.meta.title) {
    document.title = `${to.meta.title} — ${baseTitle}`
  } else {
    document.title = baseTitle
  }
})

export default router
