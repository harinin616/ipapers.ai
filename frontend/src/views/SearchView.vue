<template>
  <div class="search">
    <div class="hero-section">
      <h1>Search Papers</h1>
      
      <SearchBox
        v-model="searchQuery"
        :is-loading="isLoading"
        @search="handleSearchBoxSearch"
      />
    </div>
    
    <!-- Search Results Section -->
    <div class="papers-container">
      <div class="recent-papers">
        <div class="sort-options-container">
          <h2>Search Results</h2>
          <div v-if="results.length > 0" class="sort-options">
            <label for="sort-by">Sort by:</label>
            <select id="sort-by" v-model="sortBy">
              <option value="relevance">Relevance</option>
              <option value="date_desc">Time</option>
            </select>
          </div>
        </div>
        
        <div v-if="isLoading" class="loading">
          <p>Searching papers...</p>
        </div>
        
        <div v-else-if="results.length === 0" class="no-results">
          <p>No results found for "{{ searchQuery }}"</p>
        </div>
        
        <div v-else-if="results.length > 0" class="papers-list">
          <!-- AI Summary Section -->
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
          
          <!-- Paper Cards -->
          <PaperCard v-for="paper in sortedResults" :key="paper.paper_id" :paper="paper" />
        </div>
        <div v-else class="search-instructions">
          <p>Enter a search query to find relevant papers.</p>
        </div>
      </div>
    </div>
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
.search {
  max-width: 1000px;
  margin: 0 auto;
}

.hero-section {
  text-align: center;
  padding: 2rem 0;
  margin-bottom: 2rem;
}

.hero-section h1 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #3f51b5;
  text-align: center;
  font-size: 2rem;
}

.papers-container {
  margin-bottom: 3rem;
}

.recent-papers {
  margin-bottom: 2rem;
  padding: 0 0.5rem;
  box-sizing: border-box;
  max-width: 100%;
}

.recent-papers h2 {
  margin-bottom: 1.5rem;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 0.75rem;
  font-size: 1.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sort-options-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}



.sort-options label {
  margin-right: 0.5rem;
  color: #555;
  font-size: 0.9rem;
}

.sort-options select {
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #ccc;
  font-size: 0.9rem;
}

.papers-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  overflow: hidden;
}

.loading, .no-results, .search-instructions {
  text-align: center;
  padding: 2rem;
  color: #666;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin: 1rem 0;
}

@media (max-width: 768px) {
  .papers-list {
    grid-template-columns: 1fr;
  }
  
  .sort-options-container {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .sort-options {
    align-self: flex-end;
  }
}
</style> 