<template>
  <div class="home">
    <section class="hero-section">
      <p class="eyebrow">Research, made readable</p>
      <h1 class="hero-title">Find, read and organize<br class="br-lg" /> the papers that matter.</h1>
      <p class="hero-sub">Search across arXiv, bioRxiv and medRxiv, chat with any paper, and keep your reading in one place.</p>
      <SearchBox v-model="searchQuery" :is-loading="false" @search="handleSearch" />
      <div class="examples" aria-label="Example searches">
        <span class="examples-label">Try</span>
        <button v-for="q in examples" :key="q" type="button" class="chip example-chip" @click="runExample(q)">{{ q }}</button>
      </div>
    </section>

    <section class="papers-container" aria-labelledby="recent-heading">
      <div class="section-head">
        <h2 id="recent-heading">Recent papers</h2>
        <span v-if="paperCount" class="count-note">{{ Number(paperCount).toLocaleString() }} in the library</span>
      </div>

      <div v-if="isLoading" class="papers-list" aria-busy="true" aria-live="polite">
        <div v-for="n in 4" :key="n" class="card skeleton-card">
          <div class="skeleton" style="height:14px;width:90px"></div>
          <div class="skeleton" style="height:22px;width:80%;margin-top:14px"></div>
          <div class="skeleton" style="height:14px;width:45%;margin-top:12px"></div>
          <div class="skeleton" style="height:14px;width:100%;margin-top:18px"></div>
          <div class="skeleton" style="height:14px;width:92%;margin-top:8px"></div>
        </div>
      </div>

      <div v-else-if="papers.length === 0" class="empty card">
        <div class="empty-icon" aria-hidden="true">📄</div>
        <h3>No papers yet</h3>
        <p>The library is empty right now. New papers appear here after the next ingestion run.</p>
      </div>

      <div v-else class="papers-list">
        <PaperCard v-for="paper in papers" :key="paper.paper_id" :paper="paper" />
      </div>

      <div v-if="papers.length > 0 && hasMorePapers" class="section-load-more">
        <button @click="loadMoreRecent" :disabled="isLoadingMoreRecent" class="btn">
          {{ isLoadingMoreRecent ? 'Loading…' : 'Load more' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script>
import { defineComponent, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PaperCard from '../components/PaperCard.vue'
import SearchBox from '../components/SearchBox.vue'

import api from '../services/api'
import { searchStore } from '../stores/searchStore'

export default defineComponent({
  name: 'HomeView',
  
  components: {
    PaperCard,
    SearchBox
  },
  
  setup() {
    const router = useRouter();
    
    // define refs
    const papers = ref([]);
    const paperCount = ref(null);
    const isLoading = ref(false);
    const isLoadingMoreRecent = ref(false);
    const offset = ref(0);
    const limit = ref(10);
    const hasMorePapers = ref(true);
    const searchQuery = ref('');


    // Handle search
    const handleSearch = (query, includeSummary = false) => {
      // Clear previous search cache when starting a new search
      searchStore.clearSearch();
      
      // Store the includeSummary flag so SearchView can pick it up
      searchStore.setIncludeSummary(includeSummary);
      
      router.push({ 
        name: 'search',
        query: { q: query }
      });
    };

    // Load recent papers
    const loadPapers = async () => {
      try {
        isLoading.value = true;
        papers.value = await api.getRecentPapers(limit.value, null, 0);
        offset.value = papers.value.length;
        paperCount.value = await api.countPapers();
        hasMorePapers.value = papers.value.length < (paperCount.value || 0);
      } catch (error) { console.error('Error loading papers:', error); }
      finally { isLoading.value = false; }
    };

    // Load more recent papers
    const loadMoreRecent = async () => {
      try {
        isLoadingMoreRecent.value = true;
        const morePapers = await api.getRecentPapers(limit.value,null, offset.value);
        papers.value = [...papers.value, ...morePapers];
        offset.value += morePapers.length;
        hasMorePapers.value = morePapers.length === limit.value;
      } catch (error) { console.error('Error loading more recent papers:', error); }
      finally { isLoadingMoreRecent.value = false; }
    };

    const examples = ['large language models', 'protein folding', 'diffusion models', 'quantum error correction'];
    const runExample = (q) => { searchQuery.value = q; handleSearch(q, true); };

    onMounted(() => {
      loadPapers();
    });
    
    // return all refs and methods
    return {
      papers, paperCount, isLoading, 
      isLoadingMoreRecent, loadMoreRecent,
      offset, limit, hasMorePapers,
      searchQuery, handleSearch, examples, runExample

    };
  }
})
</script>

<style scoped>
.home { max-width: var(--content-w); margin: 0 auto; padding: 0 var(--sp-5); width: 100%; box-sizing: border-box; }

.hero-section { text-align: center; padding: var(--sp-8) 0 var(--sp-6); }
.eyebrow { margin: 0 0 var(--sp-3); font-size: var(--fs-xs); font-weight: 600; letter-spacing: .12em; text-transform: uppercase; color: var(--accent); }
.hero-title { margin: 0; font-family: var(--font-serif); font-weight: 600; font-size: clamp(2rem, 5vw, 3.1rem); line-height: 1.12; letter-spacing: -.02em; }
.hero-sub { max-width: 560px; margin: var(--sp-4) auto var(--sp-6); font-size: var(--fs-lg); color: var(--text-2); }
.examples { display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: var(--sp-2); margin-top: var(--sp-5); }
.examples-label { font-size: var(--fs-xs); color: var(--text-3); text-transform: uppercase; letter-spacing: .08em; margin-right: 2px; }
.example-chip { cursor: pointer; transition: background .15s, color .15s, border-color .15s; }
.example-chip:hover { background: var(--accent-soft); color: var(--accent); border-color: transparent; }

.papers-container { padding-bottom: var(--sp-6); }
.section-head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-3); margin-bottom: var(--sp-4); padding-bottom: var(--sp-3); border-bottom: 1px solid var(--border); }
.section-head h2 { margin: 0; font-size: var(--fs-xl); }
.count-note { font-size: var(--fs-sm); color: var(--text-3); }

.skeleton-card { padding: var(--sp-5); margin-bottom: var(--sp-3); }
.empty { text-align: center; padding: var(--sp-7) var(--sp-5); }
.empty-icon { font-size: 2rem; }
.empty h3 { margin: var(--sp-2) 0 var(--sp-1); }
.empty p { margin: 0 auto; max-width: 420px; color: var(--text-2); font-size: var(--fs-sm); }
.section-load-more { display: flex; justify-content: center; margin-top: var(--sp-5); }

@media (min-width: 900px) { .br-lg { display: inline; } }
@media (max-width: 899px) { .br-lg { display: none; } }
@media (max-width: 600px) { .hero-section { padding: var(--sp-6) 0 var(--sp-5); } .home { padding: 0 var(--sp-4); } }
</style> 