import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import { trackPageView } from '@/utils/analytics'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: {
      title: 'Home - iPapers',
      requiresAuth: false
    }
  },
  {
    path: "/chat",
    name: "chat",
    component: () => import("../views/ChatView.vue"),
    meta: {
      title: 'Chat - iPapers',
      requiresAuth: false
    }
  },
  {
    path: '/search',
    name: 'search',
    component: () => import('../views/SearchView.vue'),
    meta: {
      title: 'Search Papers - iPapers',
      requiresAuth: false
    }
  },
  {
    path: '/paper/:id/:platform?',
    name: 'paper-detail',
    component: () => import('../views/PaperDetailView.vue'),
    props: route => ({
      id: route.params.id,
      platform: route.params.platform || 'arxiv'
    }),
    meta: {
      title: 'Paper Details - iPapers',
      requiresAuth: false
    }
  },
  {
    path: '/monitor',
    name: 'paper-monitor',
    component: () => import('../views/MonitorView.vue'),
    meta: {
      title: 'Paper Monitor - iPapers',
      requiresAuth: false
    }
  },
  {
    path: '/rwf',
    name: 'related-work-forum',
    component: () => import('../views/ShareView.vue'),
    meta: {
      title: 'Related Work Forum - iPapers',
      requiresAuth: false
    },
      props: { folderId: null } 
  },

    /* 带参数：真正打开某个文件夹 */
    {
      path: '/rwf/:folderId(\\d+)',
      name: 'shareFolder',
      component: () => import('@/views/ShareView.vue'),
      props: route => ({ folderId: Number(route.params.folderId) })   // 动态传
    },

  {
    path: '/chat',
    name: 'chat',
    component: () => import('../views/ChatView.vue'),
    meta: {
      title: 'Chat - iPapers',
      requiresAuth: false
    }
  },
  {
    path: '/review',
    name: 'review',
    component: () => import('../views/Review.vue'),
    meta: {
      title: 'Review - iPapers',
      requiresAuth: false
    }
  },
  {
    path: '/daily-feed',
    name: 'daily-feed',
    component: () => import('@/views/DailyFeedView.vue'),
    meta: {
      title: 'Daily Feed - iPapers',
      requiresAuth: false
    }
  },
  {
    path: '/subscription',
    name: 'subscription',
    component: () => import('@/views/SubscriptionView.vue'),
    meta: {
      title: 'Email Subscription - iPapers',
      requiresAuth: false
    }
  },
  {
    path: '/contact',
    name: 'Contact',
    component: () => import('@/views/ContactView.vue'),
     meta: {
      title: 'Contact Us - iPapers',
      requiresAuth: false
    }
  },
  {
    path: '/terms-of-use',
    name: 'terms',
    component: () => import('../views/TermsView.vue'),
    meta: {
      title: 'Terms of Use - iPapers',
      requiresAuth: false
    }
  },
  {
    path: '/privacy-policy',
    name: 'privacy',
    component: () => import('../views/PrivacyView.vue'),
    meta: {
      title: 'Privacy Policy - iPapers',
      requiresAuth: false
    }
  },
  {
    path: '/share/:share_id',
    name: 'home-share',
    component: HomeView,
    props: route => ({
      share_id: route.params.share_id
    }),
    meta: { title: 'Home - iPapers', requiresAuth: false }
  },
  {
    // Catch all route (404)
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue'),
    meta: {
      title: '404 Not Found - iPapers',
      requiresAuth: false
    }
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('../views/ProfileView.vue'),
    meta: {
      title: 'User Profile - iPapers',
      requiresAuth: false
    }
  },
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
  document.title = to.meta.title as string || 'iPapers';

  // Continue navigation
  next();
});

router.afterEach((to, from) => {
  if (to.fullPath !== from.fullPath) {
    trackPageView(to)
  }
})

export default router 