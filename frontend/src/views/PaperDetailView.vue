<template>
  <div class="paper-detail">
    <div v-if="isLoading" class="state card" aria-busy="true">
      <div class="skeleton" style="height:30px;width:80%"></div>
      <div class="skeleton" style="height:14px;width:50%;margin-top:16px"></div>
      <div class="skeleton" style="height:14px;width:100%;margin-top:28px"></div>
      <div class="skeleton" style="height:14px;width:94%;margin-top:8px"></div>
    </div>

    <div v-else-if="error" class="state card error" role="alert">
      <h3>We couldn't load this paper</h3>
      <p>{{ error }}</p>
      <button @click="goBack" class="btn">Go back</button>
    </div>

    <div v-else-if="paper" :class="['paper-container', { 'split-layout': showPdf }]">
      <article class="paper-content">
        <button @click="goBack" class="btn btn-ghost btn-sm back-link">← Back</button>

        <header class="paper-header">
          <div class="meta-top">
            <span v-if="paper.platform" class="chip chip-accent">{{ paper.platform.toUpperCase() }}</span>
            <time class="date" :datetime="paper.published_date">{{ formattedDate }}</time>
          </div>
          <h1 class="paper-title">{{ paper.title }}</h1>
          <p class="authors">{{ paper.authors.join(', ') }}</p>
          <div v-if="paper.categories && paper.categories.length" class="paper-categories">
            <span v-for="category in paper.categories" :key="category" class="chip">{{ category }}</span>
          </div>
        </header>

        <div class="paper-actions">
          <button @click="togglePdfViewer" class="btn btn-primary">{{ showPdf ? 'Hide PDF' : 'Preview PDF' }}</button>
          <a :href="paper.pdf_url" target="_blank" rel="noopener" class="btn">Open PDF ↗</a>
          <ChatButton :paper-id="paper.paper_id" :platform="paper.platform" size="md" />
        </div>

        <section class="paper-abstract">
          <h2>Abstract</h2>
          <p>{{ paper.abstract }}</p>
        </section>
      </article>

      <aside v-if="showPdf && paper.pdf_url" class="pdf-section" aria-label="PDF preview">
        <button @click="closePdf" class="close-pdf-btn" title="Close PDF" aria-label="Close PDF">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
        </button>
        <embed :src="paper.pdf_url" class="pdf-iframe" type="application/pdf" />
      </aside>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { paperStore } from '../stores/paperStore'
import type { Paper } from '../types/paper'
import ChatButton from '../components/ChatButton.vue'
import api from '../services/api'

export default defineComponent({
  name: 'PaperDetailView',
  
  components: {
    ChatButton
  },

  props: {
    id: {
      type: String,
      required: true
    },
    platform: {
      type: String,
      default: 'arxiv'
    }
  },
  
  setup(props) {
    const router = useRouter();
    const paper = ref<Paper | null>(null);
    const isLoading = ref(true);
    const error = ref('');
    const showPdf = ref(false);
    
    // Format the date
    const formattedDate = computed(() => {
      if (!paper.value || !paper.value.published_date) return '';
      
      try {
        const date = new Date(paper.value.published_date);
        return date.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        });
      } catch (e) {
        return paper.value.published_date;
      }
    });
    
    // Toggle PDF viewer
    const togglePdfViewer = () => {
      showPdf.value = !showPdf.value;
    };
    
    // Close PDF viewer
    const closePdf = () => {
      showPdf.value = false;
    };
    
    // Go back
    const goBack = () => {
      if (document.referrer.includes(window.location.host)) {
        const referrer = new URL(document.referrer).pathname;
        sessionStorage.setItem(`scrollPos-${referrer}`, '0');
      }
      router.go(-1);
    };
    
    // 修改获取论文的方法，传递paperId和platform参数
    const fetchPaperDetails = async (paperId: string, platform: string = "arxiv") => {
      isLoading.value = true;
      error.value = '';
      
      try {
        // Check if paper exists in store first
        const cachedPaper = paperStore.getCurrentPaper();
        if (cachedPaper && cachedPaper.paper_id === paperId && cachedPaper.platform === platform) {
          paper.value = cachedPaper;
          // Still record click in backend
          await api.click_paper(paperId, platform);
        } else {
          const response = await api.get_paper(paperId, platform);
          if (response) {
            paper.value = response;
            // Update store
            paperStore.setCurrentPaper(response);
          } else {
            error.value = "Paper not found";
          }
        }
      } catch (err) {
        console.error("Error fetching paper:", err);
        error.value = "Failed to load the paper. Please try again.";
      } finally {
        isLoading.value = false;
      }
    };

    onMounted(async () => {
      // 首先确保用户ID已设置
      if (!localStorage.getItem('X-User-ID')) {
        try {
          const userId = await api.getUserId();
          localStorage.setItem('X-User-ID', userId);
        } catch (err) {
          console.error("Failed to get user ID:", err);
        }
      }
      
      // 然后获取论文详情
      await fetchPaperDetails(props.id, props.platform);
    });
    
    return {
      paper,
      isLoading,
      error,
      showPdf,
      formattedDate,
      togglePdfViewer,
      goBack,
      closePdf
    };
  }
})
</script>

<style scoped>
.paper-detail { max-width: 860px; margin: 0 auto; padding: var(--sp-5); width: 100%; box-sizing: border-box; }
.state { padding: var(--sp-6); }
.state.error { text-align: center; }
.state.error h3 { margin-top: 0; }
.state.error p { color: var(--text-2); }

.paper-content { padding: var(--sp-2) 0; }
.back-link { margin-bottom: var(--sp-4); margin-left: calc(var(--sp-3) * -1); }
.meta-top { display: flex; align-items: center; gap: var(--sp-3); }
.date { font-size: var(--fs-sm); color: var(--text-3); }
.paper-title { margin: var(--sp-3) 0 var(--sp-2); font-family: var(--font-serif); font-weight: 600; font-size: clamp(1.6rem, 3.4vw, 2.2rem); line-height: 1.2; letter-spacing: -.015em; }
.authors { margin: 0 0 var(--sp-3); color: var(--text-2); font-size: var(--fs-md); }
.paper-categories { display: flex; flex-wrap: wrap; gap: 6px; }
.paper-actions { display: flex; flex-wrap: wrap; gap: var(--sp-2); margin: var(--sp-5) 0; padding: var(--sp-4) 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
.paper-abstract h2 { margin: 0 0 var(--sp-3); font-size: var(--fs-lg); text-transform: uppercase; letter-spacing: .08em; color: var(--text-3); font-family: var(--font-sans); font-weight: 600; }
.paper-abstract p { margin: 0; font-family: var(--font-serif); font-size: 1.125rem; line-height: 1.75; color: var(--text); }

/* split layout (text + PDF) */
.paper-detail:has(.split-layout) { max-width: none; }
.split-layout { display: flex; gap: var(--sp-5); align-items: flex-start; }
.split-layout .paper-content { flex: 0 0 38%; min-width: 340px; max-height: calc(100vh - var(--header-h) - 48px); overflow-y: auto; padding-right: var(--sp-3); }
.split-layout .pdf-section { position: relative; flex: 1; height: calc(100vh - var(--header-h) - 48px); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); overflow: hidden; }
.pdf-iframe { width: 100%; height: 100%; border: 0; }
.close-pdf-btn { position: absolute; top: 10px; right: 10px; z-index: 2; display: grid; place-items: center; width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--border-strong); background: var(--surface); color: var(--text); cursor: pointer; box-shadow: var(--shadow-1); }
.close-pdf-btn:hover { background: var(--surface-2); }
@media (max-width: 900px) {
  .split-layout { flex-direction: column; }
  .split-layout .paper-content { flex: none; min-width: 0; max-height: none; padding-right: 0; }
  .split-layout .pdf-section { width: 100%; height: 70vh; }
}
</style> 