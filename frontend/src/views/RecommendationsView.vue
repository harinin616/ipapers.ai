<template>
  <div class="recommendations-page">
    <div class="header-section">
      <h1>Paper Recommendations</h1>
      <p class="subtitle">Discover papers similar to your collection</p>
    </div>

    <!-- Folder Selection -->
    <div class="recommendation-controls">
      <div class="control-group">
        <label for="folder-select">Select folder for recommendations:</label>
        <select id="folder-select" v-model="selectedFolderId" class="folder-select">
          <option value="">Choose a folder...</option>
          <option v-for="folder in userFolders" :key="folder.id" :value="folder.id">
            {{ folder.name }} ({{ folder.files.length }} papers)
          </option>
        </select>
      </div>

      <!-- Generate Button -->
      <button
        @click="generateRecommendations"
        :disabled="isLoading || !selectedFolderId"
        class="generate-btn"
      >
        <span v-if="isLoading">Generating...</span>
        <span v-else>Generate Recommendations</span>
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading">
      <p>Finding similar papers...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-message">
      <p>{{ error }}</p>
      <button @click="clearError" class="clear-error-btn">Dismiss</button>
    </div>

    <!-- Empty State -->
    <div v-if="!isLoading && !error && recommendations.length === 0 && hasSearched" class="empty-state">
      <p>No recommendations found. Try selecting a different folder or add more papers to your selected folder.</p>
    </div>

    <!-- Recommendations Results -->
    <div v-if="recommendations.length > 0" class="recommendations-section">
      <div class="results-header">
        <h2>Recommended Papers ({{ recommendations.length }})</h2>
        <div class="sort-options">
          <label for="sort-by">Sort by:</label>
          <select id="sort-by" v-model="sortBy" class="sort-select">
            <option value="relevance">Relevance</option>
            <option value="date_desc">Newest first</option>
            <option value="date_asc">Oldest first</option>
          </select>
        </div>
      </div>

      <div class="papers-list">
        <PaperCard 
          v-for="paper in sortedRecommendations" 
          :key="`${paper.paper_id}-${paper.platform}`" 
          :paper="paper" 
        />
      </div>
    </div>

    <!-- Initial State -->
    <div v-if="!hasSearched && !isLoading" class="initial-state">
      <div class="welcome-content">
        <h3>Welcome to Paper Recommendations</h3>
        <p>Get personalized paper recommendations based on papers in your selected folder.</p>
        <ul>
          <li><strong>Select a folder:</strong> Choose a folder containing papers you're interested in</li>
          <li><strong>Get recommendations:</strong> We'll find similar papers based on your folder's content</li>
        </ul>
        <p>Select a folder above and click "Generate Recommendations" to get started.</p>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../services/api'
import PaperCard from '../components/PaperCard.vue'

export default {
  name: 'RecommendationsView',
  components: {
    PaperCard
  },
  data() {
    return {
      selectedFolderId: '',
      sortBy: 'relevance',

      userFolders: [],
      recommendations: [],

      isLoading: false,
      error: null,
      hasSearched: false
    }
  },
  computed: {
    sortedRecommendations() {
      const sorted = [...this.recommendations]
      
      switch (this.sortBy) {
        case 'date_desc':
          return sorted.sort((a, b) => new Date(b.published_date) - new Date(a.published_date))
        case 'date_asc':
          return sorted.sort((a, b) => new Date(a.published_date) - new Date(b.published_date))
        case 'relevance':
        default:
          // Keep original order (already sorted by relevance from API)
          return sorted
      }
    }
  },
  async mounted() {
    await this.loadUserFolders()
  },
  methods: {
    async loadUserFolders() {
      try {
        this.userFolders = await api.get_user_folders()
      } catch (error) {
        console.error('Error loading user folders:', error)
        this.error = 'Failed to load your folders. Please refresh the page.'
      }
    },
    
    async generateRecommendations() {
      if (!this.selectedFolderId) {
        this.error = 'Please select a folder first.'
        return
      }

      this.isLoading = true
      this.error = null
      this.hasSearched = true

      try {
        const recommendations = await api.getFolderRecommendations(this.selectedFolderId, {
          limit: 30,
          exclude_existing: true
        })

        this.recommendations = recommendations || []

        if (this.recommendations.length === 0) {
          this.error = 'No recommendations found. Try selecting a different folder or add more papers to your selected folder.'
        }

      } catch (error) {
        console.error('Error generating recommendations:', error)
        this.error = 'Failed to generate recommendations. Please try again.'
      } finally {
        this.isLoading = false
      }
    },
    
    clearError() {
      this.error = null
    }
  }
}
</script>

<style scoped>
.recommendations-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.header-section {
  text-align: center;
  margin-bottom: 2rem;
}

.header-section h1 {
  font-size: 2.5rem;
  color: var(--text);
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 1.1rem;
  color: #7f8c8d;
  margin: 0;
}

.recommendation-controls {
  background: var(--surface-2);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: end;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 150px;
}

.control-group label {
  font-weight: 600;
  color: var(--text);
  font-size: 0.9rem;
}

.folder-select,
.sort-select {
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.9rem;
  background: var(--surface);
}

.generate-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
  height: fit-content;
}

.generate-btn:hover:not(:disabled) {
  background: #2980b9;
}

.generate-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #7f8c8d;
}

.error-message {
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 1rem;
  color: #c33;
}

.clear-error-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  cursor: pointer;
  margin-left: 1rem;
}

.empty-state,
.initial-state {
  text-align: center;
  padding: 3rem 2rem;
  color: #7f8c8d;
}

.welcome-content h3 {
  color: var(--text);
  margin-bottom: 1rem;
}

.welcome-content ul {
  text-align: left;
  max-width: 500px;
  margin: 1.5rem auto;
}

.welcome-content li {
  margin-bottom: 0.5rem;
}

.recommendations-section {
  margin-top: 2rem;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.results-header h2 {
  color: var(--text);
  margin: 0;
}

.sort-options {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sort-options label {
  font-weight: 600;
  color: var(--text);
  font-size: 0.9rem;
}

.papers-list {
  display: grid;
  gap: 1rem;
}

/* Responsive Design */
@media (max-width: 768px) {
  .recommendations-page {
    padding: 1rem;
  }

  .header-section h1 {
    font-size: 2rem;
  }

  .recommendation-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .control-group {
    min-width: auto;
  }

  .results-header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
