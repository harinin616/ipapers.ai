import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import { trackPageView } from '@/utils/analytics'

// Define routes with proper types
const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: {
      title: 'Home - iPaper',
      requiresAuth: false
    }
  },
  {
    path: '/search',
    name: 'search',
    component: () => import('../views/SearchView.vue'),
    meta: {
      title: 'Search Papers - iPaper',
      requiresAuth: false
    }
  },
  {
    path: '/paper',
    name: 'paper-detail',
    component: () => import('../views/PaperDetailView.vue'),
    meta: {
      title: 'Paper Details - iPaper',
      requiresAuth: false
    }
  },
  {
    path: '/monitor',
    name: 'paper-monitor',
    component: () => import('../views/MonitorView.vue'),
    meta: {
      title: 'Paper Monitor - iPaper',
      requiresAuth: false
    }
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('../views/ChatView.vue'),
    meta: {
      title: 'Chat - iPaper',
      requiresAuth: false
    }
  },
  {
    path: '/review',
    name: 'review',
    component: () => import('../views/Review.vue'),
    meta: {
      title: 'Review - iPaper',
      requiresAuth: false
    }
  },
  {
    path: '/contact',
    name: 'Contact',
    component: () => import('@/views/ContactView.vue'),
     meta: {
      title: 'Contact Us - iPaper',
      requiresAuth: false
    }
  },
  {
    path: '/terms-of-use',
    name: 'terms',
    component: () => import('../views/TermsView.vue'),
    meta: {
      title: 'Terms of Use - iPaper',
      requiresAuth: false
    }
  },
  {
    path: '/privacy-policy',
    name: 'privacy',
    component: () => import('../views/PrivacyView.vue'),
    meta: {
      title: 'Privacy Policy - iPaper',
      requiresAuth: false
    }
  },
  {
    path: '/share/:share_id',
    name: 'home-share',
    component: HomeView,              // ← 改为 HomeView
    props: route => ({                // ← 可选：把 share_id 当 prop 传下去
      share_id: route.params.share_id
    }),
    meta: { title: 'Home - iPaper', requiresAuth: false }
  },
  {
    // Catch all route (404)
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue'),
    meta: {
      title: '404 Not Found - iPaper',
      requiresAuth: false
    }
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('../views/ProfileView.vue'),
    meta: {
      title: 'User Profile - iPaper',
      requiresAuth: false
    }
  }

]

// Create router instance
const router = createRouter({
  history: createWebHistory('/'),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // If there's a saved position, use it
    if (savedPosition) {
      return savedPosition;
    }
    
    // Check if there's a saved scroll position in sessionStorage for this route
    const savedScrollPos = sessionStorage.getItem(`scrollPos-${to.fullPath}`);
    if (savedScrollPos) {
      return { top: parseInt(savedScrollPos, 10) };
    }
    
    // Default: scroll to top
    return { top: 0 };
  }
})

// Global navigation guards
router.beforeEach((to, from, next) => {
  // Update page title
  document.title = to.meta.title as string || 'iPaper';
  
  // Continue navigation
  next();
});

router.afterEach((to, from) => {
  if (to.fullPath !== from.fullPath) {          // 防止同一路径重复计
    trackPageView(to)
  }
})

export default router 