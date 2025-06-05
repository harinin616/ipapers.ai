<template>
  <div id="app">
    <header class="app-header" ref="appHeaderRef">
      <nav>
        <router-link to="/">Home</router-link>
        <router-link to="/chat">Chat</router-link>
        <!-- <router-link to="/review">Review</router-link> -->
        <button @click="toggleFileList" class="file-list-toggle-btn" title="Toggle File List">
          <svg class="icon-svg" viewBox="0 0 24 24">
            <path d="M14,2H6C4.9,2 4,2.9 4,4V20C4,21.1 4.9,22 6,22H18C19.1,22 20,21.1 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
          </svg>
          <span v-if="fileCount > 0" class="file-count-badge">{{ fileCount }}</span>
        </button>
        <div ref="googleBtn" class="g_id_signin"></div>
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
      :user_id="userId || ''"
      class="global-file-list"
      :style="fileListStyle"
      @file-selected="handleFileSelected"
      @pdf-closed="handlePdfClosed"
      @files-updated="handleFilesUpdated"
      @update-file-count="(count: number) => fileCount = count"
      @width-update="updateFileListWidth"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted, ref, watch, onBeforeUnmount, computed } from 'vue'
import { useRouter } from 'vue-router'
import apiService from './services/api'
import FileList from './components/FileList.vue'

export default defineComponent({
  name: 'App',
  components: {
    FileList
  },
  setup() {
    const router = useRouter();
    const showFilesList = ref(false);
    const showPdf = ref(false);
    const fileListRef = ref(null);
    const fileCount = ref(0);
    const userId = ref<string | null>(null);
    
    const appHeaderRef = ref<HTMLElement | null>(null);
    const headerHeight = ref(0);
    const currentFileListActualWidth = ref('');
    const fallbackFileListWidth = ref('clamp(300px, 30vw, 450px)');

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
      showFilesList.value = true;
      showPdf.value = true;
      if (typeof count === 'number') {
        fileCount.value = count;
      }
    };
    
    // Handle paper attached event to refresh FileList
    const handlePaperAttached = () => {
      if (fileListRef.value && typeof (fileListRef.value as any).loadFiles === 'function') {
        (fileListRef.value as any).loadFiles();
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


    onMounted(async () => {
      router.beforeEach((to, from) => {
        saveScrollPosition(from.fullPath);
      });
      
      await getOrCreateUserId();

      if (appHeaderRef.value) {
        headerHeight.value = appHeaderRef.value.offsetHeight;
      }
      window.addEventListener('resize', updateHeaderHeight);
      
      // Listen for paper-attached events
      window.addEventListener('paper-attached', handlePaperAttached);

      const tryRenderGoogleButton = () => {
        if (
          window.google &&
          window.google.accounts &&
          window.google.accounts.id
        ) {
          // 初始化 Google SDK
          window.google.accounts.id.initialize({
            client_id:
              '500313985236-28j5sqcq0rte1eebccl6cs6k8f3rag3q.apps.googleusercontent.com',
            callback: (response: any) => {
              // 这里拿到的 response.credential 就是 ID Token
              // 你可以把它 POST 给后端做登录/验证
              fetch('https://ipapers.ai/api/auth/google-login', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({ credential: response.credential }),
              })
                .then((r) => r.json())
                .then((userInfo) => {
                  console.log('登录成功，用户信息：', userInfo);
                })
                .catch((err) => {
                  console.error('登录请求出错：', err);
                });
            },
          });
          // 渲染按钮到 ref 对应的 DOM 节点中
          if (googleBtn.value) {
            window.google.accounts.id.renderButton(
              googleBtn.value,
              {
                theme: 'outline',
                size: 'medium',
                type: 'standard',
                shape: 'pill',
                text: 'sign_in_with',
                logo_alignment: 'left',
              }
            );
          }
        } else {
          // 如果 SDK 还没加载，延迟 100ms 再试
          setTimeout(tryRenderGoogleButton, 100);
        }
      };
      tryRenderGoogleButton();
    });

    onBeforeUnmount(() => {
      document.body.classList.remove('pdf-active-page');
      window.removeEventListener('resize', updateHeaderHeight);
      window.removeEventListener('paper-attached', handlePaperAttached);
    });
    
    const updateHeaderHeight = () => {
      if (appHeaderRef.value) {
        headerHeight.value = appHeaderRef.value.offsetHeight;
      }
    };

    const fileListStyle = computed(() => ({
      transform: showFilesList.value ? 'translateX(0)' : 'translateX(100%)',
      top: headerHeight.value + 'px',
      height: `calc(100vh - ${headerHeight.value}px)`,
    }));

    const appContentStyle = computed(() => ({
      width: showFilesList.value 
        ? `calc(100% - ${currentFileListActualWidth.value || fallbackFileListWidth.value})` 
        : '100%',
    }));

    const updateFileListWidth = (newWidth: string) => {
      currentFileListActualWidth.value = newWidth;
    };

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
      updateFileListWidth,
      googleBtn
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
}

.app-header nav a {
  color: white;
  text-decoration: none;
  margin-right: 1rem;
  opacity: 0.8;
  transition: opacity 0.2s;
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
  margin-left: auto;
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
  width: clamp(300px, 30vw, 450px);
  background-color: #ffffff;
  box-shadow: -3px 0 10px rgba(0,0,0,0.15);
  z-index: 1050;
  transition: transform 0.3s ease-in-out;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

body.pdf-active-page {
  --app-max-width: none !important;
  --container-padding: 0 !important;
}
</style> 