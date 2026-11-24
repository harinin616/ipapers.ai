<template>
  <div id="app">
    <a href="#main" class="skip-link">Skip to content</a>
    <header class="app-header" ref="appHeaderRef">
      <div class="header-inner">
        <router-link to="/" class="brand" aria-label="iPapers home">
          <span class="brand-mark" aria-hidden="true">i</span><span class="brand-name">Papers</span>
        </router-link>

        <button class="nav-toggle" type="button" :aria-expanded="navOpen" aria-controls="primary-nav" aria-label="Toggle menu" @click="navOpen = !navOpen">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path v-if="!navOpen" d="M4 7h16M4 12h16M4 17h16"/><path v-else d="M6 6l12 12M18 6L6 18"/></svg>
        </button>

        <nav id="primary-nav" class="primary-nav" :class="{ open: navOpen }" aria-label="Main" @click="navOpen = false">
          <router-link to="/" exact-active-class="router-link-active">Home</router-link>
          <router-link to="/chat">Chat</router-link>
          <router-link to="/conversational-search">Conversational Search</router-link>
          <router-link to="/monitor">Paper Monitor</router-link>
          <router-link to="/daily-feed">Daily Feed</router-link>
          <router-link to="/contact">Contact</router-link>
        </nav>

        <div class="nav-right-section">
          <SiteMetric />

          <button class="icon-btn" type="button" :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'" :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'" @click="toggleTheme">
            <svg v-if="isDark" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
            <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
          </button>

          <div ref="googleBtn" class="g_id_signin" v-show="!user"></div>
          <div class="user-info" v-show="user">
            <div class="relative">
              <button class="user-name" type="button" :class="{ open: showUserMenu }" :aria-expanded="showUserMenu" aria-haspopup="menu" @click="toggleUserMenu">
                <img :src="user?.picture" alt="" class="avatar" referrerpolicy="no-referrer" />
                <span class="user-label">{{ user?.name }}</span>
                <svg class="chevron" viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 7l4 4 4-4"/></svg>
              </button>
              <transition name="fade-slide">
                <div v-if="showUserMenu" class="user-dropdown" role="menu">
                  <router-link to="/profile" class="dropdown-item" role="menuitem">Profile</router-link>
                  <button class="dropdown-item" role="menuitem" @click="logout">Log out</button>
                </div>
              </transition>
            </div>
          </div>

          <button @click="toggleFileList" class="file-list-toggle-btn" title="Toggle file list" aria-label="Toggle file list">
            <svg class="icon-svg" viewBox="0 0 24 24" aria-hidden="true"><path d="M14,2H6C4.9,2 4,2.9 4,4V20C4,21.1 4.9,22 6,22H18C19.1,22 20,21.1 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg>
            <span class="btn-label">Files</span>
            <span v-if="fileCount > 0" class="file-count-badge">{{ fileCount }}</span>
          </button>
        </div>
      </div>
    </header>
    
    <main id="main" class="app-content" :style="appContentStyle">
      <router-view v-slot="{ Component }">
        <keep-alive :include="['HomeView']" :max="5">
          <component :is="Component" :key="$route.fullPath" />
        </keep-alive>
      </router-view>
    </main>
    

    <FileList
      ref="fileListRef"
      v-model:show-files-list="showFilesList"
      :show-pdf="showPdf"
      :user_id="userId || ''"
      class="global-file-list"
      :style="fileListStyle"
      @file-selected="handleFileSelected"
      @pdf-closed="handlePdfClosed"
      @files-updated="handleFilesUpdated"
      @update-file-count="(count: number) => fileCount = count"
    />
    <footer class="site-footer">
      <div class="footer-inner">
        <span>© {{ new Date().getFullYear() }} iPapers</span>
        <span class="footer-links">
          <a href="/terms-of-use" target="_blank" rel="noopener">Terms of Use</a>
          <a href="/privacy-policy" target="_blank" rel="noopener">Privacy Policy</a>
        </span>
      </div>
    </footer>
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted, ref, watch, onBeforeUnmount, computed,  nextTick } from 'vue'
import { useRouter } from 'vue-router'
import apiService from './services/api'
import SiteMetric from './components/SiteMetric.vue'
import FileList from './components/FileList.vue'

// Google API type declaration
declare global {
  interface Window {
    google: {
      accounts: {
        id: {
          initialize: (config: any) => void;
          renderButton: (element: HTMLElement, config: any) => void;
        }
      }
    }
  }
}

export default defineComponent({
  name: 'App',
  components: {
    FileList,
    SiteMetric
  },
  setup() {
    const router = useRouter();
    const showFilesList = ref(false);
    const showPdf = ref(false);
    const fileListRef = ref(null);
    const fileCount = ref(0);
    const userId = ref<string | null>(null);
    const windowWidth = ref(window.innerWidth);
    

    const user = ref<{ email: string; name: string; picture: string; user_id: string } | null>(null)

    const appHeaderRef = ref<HTMLElement | null>(null);
    const headerHeight = ref(0);
    const navOpen = ref(false);
    const isDark = ref(false);
    const applyTheme = (mode: 'light' | 'dark') => {
      document.documentElement.setAttribute('data-theme', mode);
      isDark.value = mode === 'dark';
      try { localStorage.setItem('theme', mode); } catch (e) { /* storage unavailable */ }
    };
    const toggleTheme = () => applyTheme(isDark.value ? 'light' : 'dark');
    isDark.value = document.documentElement.getAttribute('data-theme') === 'dark' ||
      (!document.documentElement.getAttribute('data-theme') && window.matchMedia?.('(prefers-color-scheme: dark)').matches);
    const showUserMenu = ref(false);
    function toggleUserMenu() {
      showUserMenu.value = !showUserMenu.value;
    }
    function handleClickOutside(ev: MouseEvent) {
      const target = ev.target as HTMLElement;
      if (!target.closest('.user-name') && !target.closest('.user-dropdown')) {
        showUserMenu.value = false;
      }
    }
    onMounted(() => document.addEventListener('click', handleClickOutside));
    onBeforeUnmount(() => document.removeEventListener('click', handleClickOutside));

    const saveScrollPosition = (path: string): void => {
      sessionStorage.setItem(
        `scrollPos-${path}`,
        window.scrollY.toString()
      );
    };
    
    const getOrCreateUserId = async (): Promise<void> => {
      if (!userId.value) {
        // An id without a server-signed token can't be trusted (older sessions): start a fresh session.
        if (!localStorage.getItem('access_token')) {
          localStorage.removeItem('X-User-ID');
          localStorage.removeItem('user');
        }
        let fetchedUserId = localStorage.getItem('X-User-ID');
        if (!fetchedUserId) {
          try {
            const response = await apiService.getUserId();
            fetchedUserId = response;
            if (fetchedUserId) {
               localStorage.setItem('X-User-ID', fetchedUserId);
            }
          } catch (error) {
            console.error('Failed to get user ID:', error);
          }
        }
        if (fetchedUserId) {
          userId.value = fetchedUserId;
        }
      }
    };

    const toggleFileList = () => {
      if (showPdf.value && showFilesList.value && fileListRef.value && typeof (fileListRef.value as any).closePdf === 'function') {
        (fileListRef.value as any).closePdf();
      } else {
        showFilesList.value = !showFilesList.value;
      }
    };

    const handleFileSelected = () => {
      showPdf.value = true;
      if (!showFilesList.value) {
        showFilesList.value = true;
      }
    };

    const handlePdfClosed = () => {
      showPdf.value = false;
    };

    const handleFilesUpdated = (count?: number) => {
   //   showFilesList.value = true;
      // Don't automatically show PDF when files are updated/attached
      // PDF should only show when user manually selects a file
      if (typeof count === 'number') {
        fileCount.value = count;
      }
    };
    
    // Handle paper attached event to refresh FileList
    const handlePaperAttached = () => {
      if (fileListRef.value && typeof (fileListRef.value as any).loadFolders === 'function') {
        (fileListRef.value as any).loadFolders();
      }
    };
    
    watch(showPdf, (isPdfActive) => {
      if (isPdfActive) {
        document.body.classList.add('pdf-active-page');
      } else {
        document.body.classList.remove('pdf-active-page');
      }
    });
    const googleBtn = ref<HTMLElement | null>(null);
    const tryRenderGoogleButton = () => {
        if (
          window.google &&
          window.google.accounts &&
          window.google.accounts.id
        ) {
          window.google.accounts.id.initialize({
            client_id:
              '771067338917-gv0hiqa3vdjap5b471jdh4gemo1usa7s.apps.googleusercontent.com',
            callback: (response: any) => {
         
              fetch('/api/auth/google-login', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({ credential: response.credential }),
              })
                .then((r) => r.json())
                .then((userInfo) => {
  
                  user.value = {
                    email: userInfo.email,
                    name: userInfo.name,
                    picture: userInfo.picture,
                    user_id: userInfo.user_id
                  }
 
                  localStorage.setItem(
                    'user',
                    JSON.stringify(user.value)
                  )
                  userId.value = userInfo.user_id
                  localStorage.setItem('X-User-ID', userInfo.user_id)
                  if (userInfo.access_token) localStorage.setItem('access_token', userInfo.access_token)
                  
                  // Refresh page after successful login
                  window.location.reload()
                })
                .catch((err) => {
                  console.error('Login request failed:', err)
                })
            },
          })

          if (googleBtn.value) {
            window.google.accounts.id.renderButton(googleBtn.value, {
              theme: 'outline',
              size: 'medium',
              type: 'standard',
              shape: 'pill',
              text: 'sign_in_with',
              logo_alignment: 'left',
            })
          }
        } else {
          setTimeout(tryRenderGoogleButton, 100)
        }
      }
    onMounted(async () => {
      const stored = localStorage.getItem('user')
      if (stored) {
        try {
          user.value = JSON.parse(stored)
        } catch (e) {
          console.error('Failed to parse user cache:', e)
          localStorage.removeItem('user')
          user.value = null
        }
      }

      router.beforeEach((to, from) => {
        saveScrollPosition(from.fullPath);
      });
      
      await getOrCreateUserId();

      if (appHeaderRef.value) {
        headerHeight.value = appHeaderRef.value.offsetHeight;
      }
      window.addEventListener('resize', updateHeaderHeight);
      window.addEventListener('resize', updateWindowWidth);
      
      // Listen for paper-attached events
      window.addEventListener('paper-attached', handlePaperAttached);

      if (!user.value) {
        tryRenderGoogleButton()
      }
    });

    onBeforeUnmount(() => {
      document.body.classList.remove('pdf-active-page');
      window.removeEventListener('resize', updateHeaderHeight);
      window.removeEventListener('resize', updateWindowWidth);
      window.removeEventListener('paper-attached', handlePaperAttached);
    });
    
    const updateHeaderHeight = () => {
      if (appHeaderRef.value) {
        headerHeight.value = appHeaderRef.value.offsetHeight;
      }
    };

    const updateWindowWidth = () => {
      windowWidth.value = window.innerWidth;
    };

    const fileListStyle = computed(() => ({
      transform: showFilesList.value ? 'translateX(0)' : 'translateX(100%)',
      top: headerHeight.value + 'px',
      height: `calc(100vh - ${headerHeight.value}px)`,
    }));

    const appContentStyle = computed(() => {
      if (windowWidth.value <= 1024) {
        return {
          width: '100%',
          transition: 'width 0.3s ease-in-out',
        };
      }
      

      
      return {
        width: showFilesList.value 
          ? `calc(100% - ${showPdf.value ? 'clamp(580px, 45vw, 750px)' : '340px'})` 
          : '100%',
        transition: 'width 0.3s ease-in-out, margin-right 0.3s ease-in-out',
        marginRight: showFilesList.value ? '20px' : '0px',
      };
    });

    const logout = async () => {
      user.value = null
      localStorage.removeItem('user')
      localStorage.removeItem('X-User-ID')
      localStorage.removeItem('access_token')
      userId.value = null
      await getOrCreateUserId()
 
      tryRenderGoogleButton()
      
      // Refresh page after logout
      window.location.reload()
    }

    return {
      showFilesList,
      showPdf,
      fileListRef,
      fileCount,
      userId,
      toggleFileList,
      handleFileSelected,
      handlePdfClosed,
      handleFilesUpdated,
      appHeaderRef,
      fileListStyle,
      appContentStyle,
      googleBtn,
      showUserMenu,
      toggleUserMenu,
      navOpen,
      isDark,
      toggleTheme,
      user,
      logout,
    };
  }
})
</script>

<style>
#app { display: flex; flex-direction: column; min-height: 100vh; }

.skip-link { position: absolute; left: -999px; top: 8px; z-index: 2000; background: var(--accent); color: var(--accent-ink); padding: .5rem 1rem; border-radius: var(--r-md); }
.skip-link:focus { left: 8px; }

/* ---------- Header ---------- */
.app-header {
  position: sticky; top: 0; z-index: 1000;
  background: color-mix(in srgb, var(--surface) 86%, transparent);
  backdrop-filter: saturate(160%) blur(12px);
  -webkit-backdrop-filter: saturate(160%) blur(12px);
  border-bottom: 1px solid var(--border);
}
.header-inner { display: flex; align-items: center; gap: var(--sp-5); height: var(--header-h); padding: 0 var(--sp-5); max-width: 1400px; margin: 0 auto; box-sizing: border-box; }

.brand { display: inline-flex; align-items: center; gap: 2px; text-decoration: none; color: var(--text); font-weight: 700; font-size: 1.2rem; letter-spacing: -.02em; }
.brand-mark { display: inline-grid; place-items: center; width: 28px; height: 28px; margin-right: 6px; border-radius: 8px; background: var(--accent); color: var(--accent-ink); font-family: var(--font-serif); font-weight: 600; font-size: 1.05rem; }
.brand-name { font-family: var(--font-serif); font-weight: 600; }

.primary-nav { display: flex; align-items: center; gap: 2px; }
.primary-nav a { color: var(--text-2); text-decoration: none; font-size: var(--fs-sm); font-weight: 500; padding: .45rem .8rem; border-radius: var(--r-md); transition: background .15s, color .15s; white-space: nowrap; }
.primary-nav a:hover { background: var(--surface-2); color: var(--text); }
.primary-nav a.router-link-active { color: var(--accent); background: var(--accent-soft); }

.nav-right-section { margin-left: auto; display: flex; align-items: center; gap: var(--sp-2); }

.icon-btn, .nav-toggle { display: inline-grid; place-items: center; width: 36px; height: 36px; border: 1px solid transparent; border-radius: var(--r-md); background: transparent; color: var(--text-2); cursor: pointer; transition: background .15s, color .15s; }
.icon-btn:hover, .nav-toggle:hover { background: var(--surface-2); color: var(--text); }
.nav-toggle { display: none; margin-left: auto; }

.file-list-toggle-btn { display: inline-flex; align-items: center; gap: 6px; height: 36px; padding: 0 var(--sp-3); background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--r-md); color: var(--text); font: 500 var(--fs-sm)/1 var(--font-sans); cursor: pointer; transition: background .15s; }
.file-list-toggle-btn:hover { background: var(--surface-2); }
.file-list-toggle-btn .icon-svg { width: 16px; height: 16px; fill: currentColor; }
.file-list-toggle-btn .file-count-badge { background: var(--accent); color: var(--accent-ink); font-size: 11px; font-weight: 600; min-width: 18px; height: 18px; line-height: 18px; text-align: center; padding: 0 5px; border-radius: var(--r-pill); box-sizing: border-box; }

/* user menu */
.user-info { display: flex; align-items: center; }
.relative { position: relative; }
.avatar { width: 26px; height: 26px; border-radius: 50%; object-fit: cover; }
.user-name { display: inline-flex; align-items: center; gap: 8px; height: 36px; padding: 0 var(--sp-3) 0 5px; border: 1px solid var(--border-strong); border-radius: var(--r-pill); background: var(--surface); color: var(--text); font: 500 var(--fs-sm)/1 var(--font-sans); cursor: pointer; transition: background .15s; }
.user-name:hover, .user-name.open { background: var(--surface-2); }
.user-label { max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-name .chevron { transition: transform .15s; }
.user-name.open .chevron { transform: rotate(180deg); }
.user-dropdown { position: absolute; right: 0; top: calc(100% + 8px); min-width: 180px; padding: 6px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-md); box-shadow: var(--shadow-3); z-index: 1100; }
.dropdown-item { display: block; width: 100%; text-align: left; border: none; padding: .55rem .75rem; font: 500 var(--fs-sm)/1.2 var(--font-sans); color: var(--text); background: transparent; border-radius: var(--r-sm); text-decoration: none; cursor: pointer; box-sizing: border-box; }
.dropdown-item:hover { background: var(--surface-2); }
.dropdown-item:visited, .dropdown-item.router-link-active { color: var(--text); }
.fade-slide-enter-from, .fade-slide-leave-to { opacity: 0; transform: translateY(-4px); }
.fade-slide-enter-active, .fade-slide-leave-active { transition: all .15s var(--ease); }

/* site metric (component keeps these class names) */
.metric-btn { display: inline-flex; align-items: center; gap: 6px; background: var(--surface-2); color: var(--text-2); border: 1px solid var(--border); border-radius: var(--r-pill); padding: .25rem .65rem; font-size: var(--fs-xs); font-weight: 600; cursor: pointer; transition: background .15s; }
.metric-btn:hover { background: var(--border); }
.metric-card { position: absolute; top: calc(100% + 8px); left: 50%; transform: translateX(-50%); width: 200px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-md); box-shadow: var(--shadow-3); padding: .7rem .9rem; display: flex; flex-direction: column; align-items: center; z-index: 9999; pointer-events: auto; }
.metric-card canvas { margin-bottom: 4px; }
.metric-label { margin-top: 4px; font-size: 11px; color: var(--text-3); }
@keyframes fadeSlideIn { 0% { opacity: 0; transform: translateY(4px); } 100% { opacity: 1; transform: translateY(0); } }
@keyframes fadeSlideOut { 0% { opacity: 1; transform: translateY(0); } 100% { opacity: 0; transform: translateY(4px); } }
.animate-fade-slide-in { animation: fadeSlideIn .12s ease-out forwards; }
.animate-fade-slide-out { animation: fadeSlideOut .1s ease-in forwards; }

/* ---------- Content / panels ---------- */
.app-content { flex: 1; padding: 0; max-width: none; margin: 0; display: flex; flex-direction: column; transition: width .3s var(--ease); position: relative; z-index: 1; }
.global-file-list { position: fixed; right: 0; background: var(--surface); border-left: 1px solid var(--border); box-shadow: var(--shadow-3); z-index: 100; transition: transform .3s var(--ease), width .3s var(--ease); overflow-y: auto; display: flex; flex-direction: column; will-change: transform, width; transform: translateZ(0); }
body.pdf-active-page { --app-max-width: none !important; --container-padding: 0 !important; }

/* ---------- Footer ---------- */
.site-footer { margin-top: var(--sp-7); border-top: 1px solid var(--border); background: var(--surface); }
.footer-inner { max-width: var(--content-w); margin: 0 auto; padding: var(--sp-5); display: flex; justify-content: space-between; flex-wrap: wrap; gap: var(--sp-3); font-size: var(--fs-sm); color: var(--text-3); }
.footer-links { display: inline-flex; gap: var(--sp-4); }
.site-footer a { color: var(--text-2); text-decoration: none; }
.site-footer a:hover { color: var(--accent); text-decoration: underline; }

/* ---------- Responsive ---------- */
@media (max-width: 1024px) {
  .app-content { width: 100% !important; }
  .global-file-list { z-index: 200; }
  .header-inner { gap: var(--sp-3); padding: 0 var(--sp-4); }
  .primary-nav a { padding: .45rem .55rem; }
}
@media (max-width: 860px) {
  .nav-toggle { display: inline-grid; margin-left: 0; }
  .nav-right-section { margin-left: auto; }
  .primary-nav { display: none; position: absolute; left: 0; right: 0; top: var(--header-h); flex-direction: column; align-items: stretch; padding: var(--sp-3) var(--sp-4) var(--sp-4); background: var(--surface); border-bottom: 1px solid var(--border); box-shadow: var(--shadow-2); }
  .primary-nav.open { display: flex; }
  .primary-nav a { padding: .7rem .8rem; font-size: var(--fs-md); }
  .file-list-toggle-btn .btn-label, .user-label, .metric-btn { display: none; }
  .brand-name { display: none; }
}
</style> 