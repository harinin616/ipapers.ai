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
        v-for="(section, idx) in sections"
        :key="section.id"
        :papers="section.papers || []"
        :is-loading="section.isLoading || false"
        :title="section.title"
        @remove="removeSection(idx)"
      />
      <!-- Placeholder card for adding new list -->
      <div class="add-list-placeholder" title="Add new list" @click="addSection">
        <svg class="add-icon" viewBox="0 0 24 24">
          <path d="M19 13H13V19H11V13H5V11H11V5H13V11H19V13Z" />
        </svg>
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, onMounted, watch, reactive } from 'vue'
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
    const paperCount = ref(null);
    const limit = ref(20);
    const searchQuery = ref('');
    
    const STORAGE_KEY = 'paper-sections';
    
    // Load sections from localStorage or use default
    const loadSections = () => {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed) && parsed.length > 0) {
            // Ensure each section has the required properties and is reactive
            return parsed.map(section => reactive({
              id: section.id || Date.now(),
              title: section.title || '',
              papers: [],
              isLoading: false
            }));
          }
        }
      } catch (e) {
        console.error('Failed to load sections from localStorage:', e);
      }
      return [reactive({ id: 1, title: '', papers: [], isLoading: false })];
    };
    
    // Save sections to localStorage (only save id and title, not papers)
    const saveSections = (sectionsData) => {
      try {
        const sectionsToSave = sectionsData.map(section => ({
          id: section.id,
          title: section.title
        }));
        localStorage.setItem(STORAGE_KEY, JSON.stringify(sectionsToSave));
      } catch (e) {
        console.error('Failed to save sections to localStorage:', e);
      }
    };
    
    const sections = ref(loadSections());
    
    // Watch sections for changes and save automatically
    watch(sections, (newSections) => {
      saveSections(newSections);
    }, { deep: true });

    // Handle search
    const handleSearch = (query) => {
      // Clear previous search cache when starting a new search
      searchStore.clearSearch();
      
      router.push({ 
        name: 'search',
        query: { q: query }
      });
    };

    // Load papers for a specific section
    const loadSectionPapers = async (section) => {
      try {
        section.isLoading = true;
        const keyword = section.title.trim() || '';
        const papers = await api.getRecentPapers(limit.value, keyword);
        section.papers = papers;
      } catch (error) {
        console.error(`Error loading papers for section "${section.title}":`, error);
        section.papers = [];
      } finally {
        section.isLoading = false;
      }
    };

    // Load papers for all sections
    const loadPapersForAllSections = async () => {
      try {
        paperCount.value = await api.countPapers();
        
        // Load papers for each section in parallel
        const loadPromises = sections.value.map(section => loadSectionPapers(section));
        await Promise.all(loadPromises);
      } catch (error) {
        console.error('Error loading paper count:', error);
      }
    };

    const removeSection = (index) => {
      sections.value.splice(index, 1);
    };

    const addSection = async () => {
      const input = window.prompt('Enter list keyword:');
      if (input === null) return; // user cancelled
      const title = input.trim();
      
      // Only proceed if title is not empty
      if (!title) return;
      
      const newSection = reactive({ 
        id: Date.now(), 
        title, 
        papers: [], 
        isLoading: true  // Start with loading state
      });
      
      sections.value.push(newSection);
      
      // Load papers for the new section
      await loadSectionPapers(newSection);
    };

    onMounted(() => {
      loadPapersForAllSections();
    });
    
    // return all refs and methods
    return {
      paperCount,
      limit,
      searchQuery, handleSearch,
      sections, removeSection, addSection,
      loadPapersForAllSections, loadSectionPapers
    };
  }
})
</script>

<style scoped>
.home {
  max-width: 1000px;
  width: 100%;
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.5rem;
  padding: 0 0.5rem;
  box-sizing: border-box;
  grid-auto-rows: 1fr;
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