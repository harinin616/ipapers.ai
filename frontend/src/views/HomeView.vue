<template>
  <div class="home">
    <div class="hero-section">
      <SearchBox
        v-model="searchQuery"
        :is-loading="false"
        @search="handleSearch"
      />
    </div>
    
    <!-- Papers Sections Container -->
    <div class="sections-grid">
      <ScrollablePaperList
        v-for="index in sectionCount"
        :key="index"
        :papers="papers"
        :is-loading="isLoading"
        title="Recent Papers"
      />
      <!-- Placeholder card for adding new list -->
      <div class="add-list-placeholder" title="Add new list">
        <svg class="add-icon" viewBox="0 0 24 24">
          <path d="M19 13H13V19H11V13H5V11H11V5H13V11H19V13Z" />
        </svg>
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SearchBox from '../components/SearchBox.vue'
import ScrollablePaperList from '../components/ScrollablePaperList.vue'
import api from '../services/api'
import { searchStore } from '../stores/searchStore'

export default defineComponent({
  name: 'HomeView',
  
  components: {
    SearchBox,
    ScrollablePaperList
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
    const sectionCount = 6; // Number of scrollable windows to render

    // Handle search
    const handleSearch = (query) => {
      // Clear previous search cache when starting a new search
      searchStore.clearSearch();
      
      router.push({ 
        name: 'search',
        query: { q: query }
      });
    };

    // Load recent papers
    const loadPapers = async () => {
      try {
        isLoading.value = true;
        papers.value = await api.getRecentPapers(limit.value, 0);
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
        const morePapers = await api.getRecentPapers(limit.value, offset.value);
        papers.value = [...papers.value, ...morePapers];
        offset.value += morePapers.length;
        hasMorePapers.value = morePapers.length === limit.value;
      } catch (error) { console.error('Error loading more recent papers:', error); }
      finally { isLoadingMoreRecent.value = false; }
    };

    onMounted(() => {
      loadPapers();
    });
    
    // return all refs and methods
    return {
      papers, paperCount, isLoading, 
      isLoadingMoreRecent, loadMoreRecent,
      offset, limit, hasMorePapers,
      searchQuery, handleSearch,
      sectionCount
    };
  }
})
</script>

<style scoped>
.home {
  max-width: 1000px;
  margin: 0 auto;
}

.hero-section {
  text-align: center;
  padding: 2rem 0;
  margin-bottom: 2rem;
}

.search-container {
  background-color: white;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.search-form {
  display: flex;
}

.search-input {
  flex: 1;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px 0 0 4px;
  outline: none;
}

.search-input:focus {
  border-color: #3f51b5;
}

.search-button {
  padding: 0.75rem 1.5rem;
  background-color: #3f51b5;
  color: white;
  border: none;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.2s;
}

.search-button:hover {
  background-color: #303f9f;
}

.search-button:disabled {
  background-color: #c5cae9;
  cursor: not-allowed;
}


.primary-button, .secondary-button {
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  display: inline-block;
}

.primary-button {
  background-color: #3f51b5;
  color: white;
  border: none;
}

.primary-button:hover {
  background-color: #303f9f;
}

.primary-button:disabled {
  background-color: #c5cae9;
  cursor: not-allowed;
}

.secondary-button {
  background-color: transparent;
  color: #3f51b5;
  border: 1px solid #3f51b5;
}

.secondary-button:hover {
  background-color: rgba(63, 81, 181, 0.1);
}

.secondary-button:disabled {
  color: #9fa8da;
  border-color: #9fa8da;
  cursor: not-allowed;
}

.sections-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  padding: 0 0.5rem;
  box-sizing: border-box;
}

.add-list-placeholder {
  background-color: #f8f9fa;
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s;
  height: 450px;
  width: 100%;
}

.add-list-placeholder:hover {
  background-color: #e9ecef;
}

.add-icon {
  width: 32px;
  height: 32px;
  fill: #6b7280;
}
</style> 