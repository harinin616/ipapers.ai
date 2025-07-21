<template>
  <div id="app">
    <header class="app-header" ref="appHeaderRef">
      <nav>
        <router-link to="/">Home</router-link>
        <router-link to="/chat">Chat</router-link>
        <router-link to="/monitor">Paper Monitor</router-link>
        <!--<-router-link to="/rwf">Related Work Forum</router-link>-->
        <!--<router-link to="/review">Related Work Generation</router-link>-->
        <router-link to="/daily-feed">Daily Feed</router-link>
        <router-link to="/contact">Contact Us</router-link>

        <div class="nav-right-section">
          <SiteMetric />

          <div ref="googleBtn" class="g_id_signin" v-show="!user"></div>
          <div class="user-info" v-show="user">
            <img :src="user?.picture" alt="avatar" class="avatar" />

              <div class="relative">
                <button class="user-name" @click="toggleUserMenu">
                  {{ user?.name }}
                  <svg class="chevron" viewBox="0 0 20 20"><path d="M6 7l4 4 4-4"/></svg>
                </button>


                <transition name="fade-slide">
                  <div
                    v-if="showUserMenu"
                    class="user-dropdown"
                  >
                  <router-link to="/profile" class="dropdown-item">Profile</router-link>
                  <button class="dropdown-item" @click="logout">Logout</button>
                 </div>
               </transition>
             </div>
          </div>

          <button
            @click="toggleFileList"
            class="file-list-toggle-btn"
            title="Toggle File List"
          >
            <svg class="icon-svg" viewBox="0 0 24 24">
              <path
                d="M14,2H6C4.9,2 4,2.9 4,4V20C4,21.1 4.9,22 6,22H18C19.1,22 20,21.1 20,20V8L14,2M18,20H6V4H13V9H18V20Z"
              />
            </svg>

            <span class="btn-label">&nbsp;File&nbsp;List</span>

            <span v-if="fileCount > 0" class="file-count-badge">{{ fileCount }}</span>
          </button>
        </div>

      </nav>
    </header>
    
    <main class="app-content" :style="appContentStyle">
      <router-view v-slot="{ Component }">
        <keep-alive :include="['HomeView']" :max="5">
          <component :is="Component" :key="$route.fullPath" />
        </keep-alive>
      </router-view>
    </main>
    
    <footer class="app-footer">
    </footer>

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
      <p>
        © 2025 iPapers. All rights reserved. |
        <a href="/terms-of-use" target="_blank">Terms of Use</a> |
        <a href="/privacy-policy" target="_blank">Privacy Policy</a>
      </p>
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
              '500313985236-28j5sqcq0rte1eebccl6cs6k8f3rag3q.apps.googleusercontent.com',
            callback: (response: any) => {
         
              fetch('https://ipapers.ai/api/auth/google-login', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({ credential: response.credential }),
              })
                .then((r) => r.json())
                .then((userInfo) => {
                  console.log('Login successful, user info:', userInfo)
  
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
      user,
      logout,
    };
  }
})
</script>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #f8f9fa;
  color: #333;
  line-height: 1.6;
  overflow-x: hidden;
}

#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  background-color: #3f51b5;
  color: white;
  padding: 1rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 1000;
}

.app-header h1 {
  margin: 0.5rem 0;
  font-size: 1.8rem;
  font-weight: 500;
}

.app-header nav {
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  overflow: visible;
}

.app-header nav a {
  color: white;
  text-decoration: none;
  margin-right: 1rem;
  opacity: 0.8;
  transition: opacity 0.2s;
  overflow: visible;
}

.app-header nav a:hover {
  opacity: 1;
}

.app-header nav a.router-link-active {
  opacity: 1;
  font-weight: 600;
}

.app-content {
  flex: 1;
  padding: 0;
  max-width: none;
  margin: 0;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease-in-out;
  position: relative;
  z-index: 1;
}

.app-footer {
  background-color: #f1f3f5;
  padding: 1rem;
  text-align: center;
  font-size: 0.9rem;
  color: #666;
}

.file-list-toggle-btn {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.file-list-toggle-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.file-list-toggle-btn .icon-svg {
  width: 22px;
  height: 22px;
  fill: currentColor;
}

.file-list-toggle-btn .file-count-badge {
  background-color: #f44336;
  color: white;
  font-size: 0.7rem;
  padding: 2px 5px;
  border-radius: 8px;
  margin-left: 6px;
  font-weight: bold;
}

.global-file-list {
  position: fixed;
  right: 0;
  background-color: #ffffff;
  box-shadow: -3px 0 10px rgba(0,0,0,0.15);
  z-index: 100;
  transition: transform 0.3s ease-in-out, width 0.3s ease-in-out;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  will-change: transform, width;
  transform: translateZ(0);
}

body.pdf-active-page {
  --app-max-width: none !important;
  --container-padding: 0 !important;
}
.user-info {
  display: flex;
  align-items: center;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  margin-right: 8px;
}

.user-name{
  color:#fff;font-weight:500;margin-right:12px;
  display:inline-flex;align-items:center;gap:4px;
  padding:.35rem .9rem;border:none;border-radius:9999px;
  background:rgba(255,255,255,.12);          /* ← 淡色底 */
  cursor:pointer;transition:background .15s;
}
.user-name:focus{outline:none}

/* 悬停稍深 */
.user-name:hover{background:rgba(255,255,255,.18)}

/* 展开 / 选中：背景更深，箭头翻转 */
.user-name.open{background:rgba(255,255,255,.28)}
.user-name .chevron{
  width:14px;height:14px;fill:currentColor;transition:transform .15s;
}
.user-name.open .chevron{transform:rotate(180deg)}


/* 下拉卡片 */
.user-dropdown{
  position:absolute;right:7%;top:calc(100% + 6px);
  width:160px;background:#fff;border-radius:8px;
  box-shadow:0 8px 20px rgba(0,0,0,.15);z-index:999;
  overflow:hidden;          /* 让圆角裁掉分隔线 */
}

/* 菜单项 */
.dropdown-item{
  display:block;width:100%;text-align:left;border:none;
  padding:.65rem 1rem;font-size:.875rem;color:#374151;
  background:#fff;text-decoration:none;
}
.user-dropdown{
  padding-top: 0.25rem;    /* 原本若无 padding 这行可省略 */
  padding-bottom: 0.25rem; /* 轻轻压缩上下留白 */
}

/* ② 每一行条目：高度降低 */
.dropdown-item{
  padding: .45rem .95rem;  /* 原来 .65rem 变成 .45rem */
  font-size: .85rem;       /* 若想更紧凑，可稍缩字体 */
}

.dropdown-item:visited{color:#374151}          /* 去掉浏览过后的紫色 */
.dropdown-item.router-link-active{color:#374151}/* Vue router-link 激活色 */


.dropdown-item:hover{background:#f3f4f6}
.dropdown-item + .dropdown-item{border-top:1px solid #e5e7eb}
.dropdown-item.danger{color:#dc2626}

/* 进出动画保持不变 */
.fade-slide-enter-from,
.fade-slide-leave-to{opacity:0;transform:translateY(-4px)}
.fade-slide-enter-active,
.fade-slide-leave-active{transition:all .15s ease}


.logout-btn {
  background: transparent;
  border: 1px solid white;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.nav-right-section {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.metric-btn {
  background: transparent;
  border: 1.5px solid #4ade80;  /* 清新的绿色边框 */
  color: #4ade80;
  border-radius: 9999px;
  padding: 0.25rem 0.5rem;
  font-weight: 600;
  transition: all 0.2s ease-in-out;
}
.metric-btn:hover {
  background-color: #4ade8055; /* 带透明度的高亮 */
}

.metric-btn:hover{ background:rgba(255,255,255,.4); }

.metric-btn{ background:rgba(255,255,255,.25); color:#fff;
             padding:0.15rem 0.55rem; border-radius:9999px;
             transition:background-color .15s; }


.metric-card{ 
  position: absolute;
  top: calc(100% + 8px);
  left: 80%;
  transform: translateX(-50%);
  width: 180px; 
  background: #fff; 
  border-radius: 4px;
  box-shadow: 0 6px 18px rgba(0,0,0,.18);
  padding: 0.6rem 0.9rem; 
  display: flex;
  flex-direction: column; 
  align-items: center;
  z-index: 9999;
  pointer-events: auto;
}
.metric-card canvas {
  margin-bottom: 4px; /* 根据需要调整 */
}

.metric-label{ margin-top:4px; font-size:10px; color:#6b7280 }

@keyframes fadeSlideIn{0%{opacity:0;transform:translateY(4px)}100%{opacity:1;transform:translateY(0)}}
@keyframes fadeSlideOut{0%{opacity:1;transform:translateY(0)}100%{opacity:0;transform:translateY(4px)}}
.animate-fade-slide-in{animation:fadeSlideIn .12s ease-out forwards}
.animate-fade-slide-out{animation:fadeSlideOut .1s ease-in forwards}

/* Responsive adjustments to prevent overlay issues */
@media (max-width: 1024px) {
  .app-content {
    width: 100% !important;
  }
  
  .global-file-list {
    z-index: 200;
  }
}

@media (max-width: 768px) {
  .app-content {
    width: 100% !important;
  }
  
  .global-file-list {
    z-index: 200;
  }
}
.app-header{
  padding: .5rem 1rem;        /* 原来是 1rem 1rem */
}


/* 若头像跟着显得偏低，可略缩小并垂直居中（可选） */
.avatar{
  width: 28px;
  height: 28px;
}

.nav-right-section{ gap:.6rem; }   /* 原来 1rem */

/* ② 用户名胶囊 – 方正一点 + 稍大 */
.user-name{
  font-size:0.9rem;
  padding:.45rem 1.1rem;      /* 内边距增大  → 胶囊更高更宽 */
  border-radius:8px;          /* 从圆 pill 改成 8px 圆角矩形 */
  background:rgba(255,255,255,.16);
}
.user-name:hover{background:rgba(255,255,255,.22);}
.user-name.open{background:rgba(255,255,255,.28);}

/* ②-a 让下拉箭头垂直居中且与文字保持 6px 距离 */
.user-name .chevron{
  width:14px;height:14px;fill:currentColor;transform-origin:center;
  margin-left:6px;            /* ↔ 间距 */
  transition:transform .15s;
}
.site-footer {
  margin-top: 3rem;
  padding: 1.5rem 0;
  text-align: center;
  font-size: 0.9rem;
  color: #6b7280;
  border-top: 1px solid #e5e7eb;
}

.site-footer a {
  color: #3f51b5;
  text-decoration: none;
  margin: 0 0.5rem;
}

.site-footer a:hover {
  text-decoration: underline;
}


</style> 