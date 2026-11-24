<template>
  <div class="search">
    <section class="hero-section">
      <SearchBox
        v-model="searchQuery"
        :is-loading="isLoading"
        @search="handleSearchBoxSearch"
      />
    </section>

    <section class="papers-container" aria-live="polite">
      <div class="sort-options-container">
        <h2>
          <template v-if="isLoading">Searching…</template>
          <template v-else-if="results.length > 0">{{ results.length }} result{{ results.length === 1 ? '' : 's' }}<span v-if="searchQuery" class="for-query"> for “{{ searchQuery }}”</span></template>
          <template v-else>Search results</template>
        </h2>
        <div v-if="results.length > 0" class="sort-options">
          <label for="sort-by">Sort by</label>
          <select id="sort-by" v-model="sortBy" class="select">
            <option value="relevance">Relevance</option>
            <option value="date_desc">Newest</option>
          </select>
        </div>
      </div>

      <div v-if="isLoading" class="papers-list" aria-busy="true">
        <div v-for="n in 3" :key="n" class="card skeleton-card">
          <div class="skeleton" style="height:22px;width:75%"></div>
          <div class="skeleton" style="height:14px;width:40%;margin-top:12px"></div>
          <div class="skeleton" style="height:14px;width:100%;margin-top:18px"></div>
          <div class="skeleton" style="height:14px;width:90%;margin-top:8px"></div>
        </div>
      </div>

      <div v-else-if="results.length === 0" class="empty card">
        <div class="empty-icon" aria-hidden="true">🔎</div>
        <template v-if="searchQuery">
          <h3>No papers match “{{ searchQuery }}”</h3>
          <p>Try fewer or different keywords, check the spelling, or search for a broader topic.</p>
        </template>
        <template v-else>
          <h3>Search the library</h3>
          <p>Enter a topic, method or title above to find relevant papers.</p>
        </template>
      </div>

      <div v-else class="papers-list">
        <SummaryProgress
          v-if="searchStore.getIsSummaryLoading()"
          :is-loading="searchStore.getIsSummaryLoading()"
          :paper-count="results.length"
          :error="searchStore.getSummaryError()"
          @retry="retrySummaryGeneration"
        />

        <SearchSummary
          v-else-if="summary"
          :summary="summary"
          :paper-count="results.length"
        />

        <PaperCard v-for="paper in sortedResults" :key="paper.paper_id" :paper="paper" />
      </div>
    </section>
  </div>
</template>

<script>
import api from '../services/api'
import SearchBox from '../components/SearchBox.vue'
import PaperCard from '../components/PaperCard.vue'
import SearchSummary from '../components/SearchSummary.vue'
import SummaryProgress from '../components/SummaryProgress.vue'
import { searchStore } from '../stores/searchStore'

export default {
  name: 'SearchView',
  components: {
    SearchBox,
    PaperCard,
    SearchSummary,
    SummaryProgress
  },
  data() {
    return {
      searchQuery: '',
      results: [],
      isLoading: false,
      sortBy: searchStore.getSortBy(),
      summary: null
    }
  },
  watch: {
    '$route.query.q': {
      immediate: true,
      handler(newQuery, oldQuery) {
        if (newQuery) {
          this.searchQuery = newQuery;
          
          // check if returning from a detail page and have cached results
          if (searchStore.hasCachedResults(newQuery)) {
            // use cached results instead of searching again
            this.results = searchStore.getResults();
            this.summary = searchStore.getSummary();
            // Note: we don't restore loading states as cache implies completion
            return;
          }
          
          // only perform search if query actually changed or don't have cached results
          if (oldQuery !== newQuery || !searchStore.getHasSearched()) {
            // Check if this is an AI search request from the home page
            const includeSummary = searchStore.getIncludeSummary();
            this.performSearch(includeSummary);
            // Reset the flag after use
            searchStore.setIncludeSummary(false);
          }
        }
      }
    }
  },
  mounted() {
    // initialize with store state if available
    if (searchStore.getHasSearched()) {
      this.searchQuery = searchStore.getQuery();
      this.results = searchStore.getResults();
      this.sortBy = searchStore.getSortBy();
      this.summary = searchStore.getSummary();
    }
  },
  computed: {
    sortedResults() {
      if (!this.results) return [];
      const resultsCopy = [...this.results];

      if (this.sortBy === 'date_desc') {
        resultsCopy.sort((a, b) => {
          const dateA = a.published_date ? new Date(a.published_date) : null;
          const dateB = b.published_date ? new Date(b.published_date) : null;

          // Handle papers with invalid/missing dates by pushing them to the end
          if (!dateA || isNaN(dateA.getTime())) return 1;
          if (!dateB || isNaN(dateB.getTime())) return -1;

          return dateB - dateA; 
        });
      }
      searchStore.setSortBy(this.sortBy);
      return resultsCopy;
    },
    searchStore() {
      return searchStore;
    }
  },
  methods: {
    handleSearchBoxSearch(query, includeSummary = false) {
      // clear cache when user performs a new search from the search box
      searchStore.clearSearch();
      this.searchQuery = query;
      // Explicitly clear summary before new search
      this.summary = null;
      this.performSearch(includeSummary);
    },
    
    async performSearch(includeSummary = false) {
      if (!this.searchQuery.trim()) return;
      
      console.log('🔍 Starting search with includeSummary:', includeSummary);
      
      this.isLoading = true;
      this.results = [];
      this.summary = null;
      
      // update store
      searchStore.setQuery(this.searchQuery.trim());
      searchStore.setSummary(null);
      searchStore.setSummaryError(null);
      
      try {
        // Step 1: Get paper results immediately (no summary)
        const data = await api.searchPapers({
          query: this.searchQuery.trim(),
          limit: 30,
          include_summary: false,  // Always false now
          summary_type: 'full'
        });
        
        console.log('📊 API response data:', { resultsCount: data.results?.length || 0 });
        
        if (data && Array.isArray(data.results)) {
          this.results = data.results.map(paper => ({
            ...paper,
            authors: Array.isArray(paper.authors) ? paper.authors : 
                     (typeof paper.authors === 'string' ? [paper.authors] : []),
            abstract: paper.abstract || 'No abstract available',
            year: paper.year || '',
            venue: paper.venue || 'Unknown venue',
            categories: Array.isArray(paper.categories) ? paper.categories : 
                       (paper.categories ? [paper.categories] : [])
          }));
          
          // update store with results
          searchStore.setResults(this.results);
          
          // Step 2: Generate summary separately if requested
          if (includeSummary && this.results.length > 0) {
            this.generateSummary();
          }
        } else {
          console.error('Invalid search results format', data);
          this.results = [];
          searchStore.setResults([]);
        }
        
        this.$router.replace({ 
          query: { q: this.searchQuery.trim() } 
        });
      } catch (error) {
        console.error('Error searching papers:', error);
        this.results = [];
        searchStore.setResults([]);
      } finally {
        this.isLoading = false;
      }
    },

    async generateSummary() {
      if (!this.results.length) return;
      
      searchStore.setIsSummaryLoading(true);
      searchStore.setSummaryError(null);
      
      try {
        console.log('🤖 Generating AI summary for', this.results.length, 'papers');
        
        const summaryData = await api.generateSearchSummary({
          query: this.searchQuery.trim(),
          papers: this.results,
          summary_type: 'full'
        });
        
        if (summaryData && summaryData.summary) {
          this.summary = summaryData.summary;
          searchStore.setSummary(summaryData.summary);
          console.log('✅ AI summary generated successfully');
        }
      } catch (error) {
        console.error('Error generating summary:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to generate AI summary';
        searchStore.setSummaryError(errorMessage);
      } finally {
        searchStore.setIsSummaryLoading(false);
      }
    },

    async retrySummaryGeneration() {
      await this.generateSummary();
    }
  }
}
</script>

<style scoped>
.search { max-width: var(--content-w); margin: 0 auto; padding: 0 var(--sp-5); width: 100%; box-sizing: border-box; }
.hero-section { padding: var(--sp-6) 0 var(--sp-5); }
.papers-container { padding-bottom: var(--sp-6); }
.sort-options-container { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-3); flex-wrap: wrap; margin-bottom: var(--sp-4); padding-bottom: var(--sp-3); border-bottom: 1px solid var(--border); }
.sort-options-container h2 { margin: 0; font-size: var(--fs-xl); }
.for-query { font-weight: 400; color: var(--text-2); }
.sort-options { display: flex; align-items: center; gap: var(--sp-2); font-size: var(--fs-sm); color: var(--text-3); }
.select { height: 34px; padding: 0 var(--sp-3); font: 500 var(--fs-sm)/1 var(--font-sans); color: var(--text); background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--r-md); cursor: pointer; }
.skeleton-card { padding: var(--sp-5); margin-bottom: var(--sp-3); }
.empty { text-align: center; padding: var(--sp-7) var(--sp-5); }
.empty-icon { font-size: 2rem; }
.empty h3 { margin: var(--sp-2) 0 var(--sp-1); }
.empty p { margin: 0 auto; max-width: 440px; color: var(--text-2); font-size: var(--fs-sm); }
@media (max-width: 600px) { .search { padding: 0 var(--sp-4); } }
</style> 