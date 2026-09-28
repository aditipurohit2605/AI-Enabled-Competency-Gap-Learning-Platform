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

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { guestOnly: true }
  },
  {
    path: '/register',
    name: 'register',
    component: LoginView,
    meta: { guestOnly: true }
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
      {
        path: 'dashboard',
        name: 'dashboard',
        component: LearnerDashboard,
        meta: { requiresAuth: true }
      },
      {
        path: 'profile',
        name: 'profile',
        component: MyProfile,
        meta: { requiresAuth: true }
      },
      {
        path: 'gap',
        name: 'gap',
        component: GapReport,
        meta: { requiresAuth: true }
      },
      {
        path: 'path',
        name: 'path',
        component: LearningPath,
        meta: { requiresAuth: true }
      },
      {
        path: 'quiz',
        name: 'quiz',
        component: QuizView,
        meta: { requiresAuth: true }
      },
      {
        path: 'history',
        name: 'history',
        component: HistoryView,
        meta: { requiresAuth: true }
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

export default router
