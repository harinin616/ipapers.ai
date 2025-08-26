<template>
  <div class="perplexity-search">
    <!-- Header removed for cleaner look -->

    <!-- Main Content -->
    <div class="main-content">
      <!-- Welcome State -->
      <div v-if="conversations.length === 0" class="welcome-state">
        <div class="welcome-card">
          <h2>👋 Welcome to Intelligent Conversational Search</h2>
          <p>I can help you:</p>
          
          <div class="feature-list">
            <div class="feature-item">
              <span class="feature-icon">🔍</span>
              <span class="feature-text"><strong>Search Papers:</strong> Describe your research needs, I'll find relevant papers</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">💬</span>
              <span class="feature-text"><strong>Academic Discussion:</strong> Explain concepts, discuss research methods</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">🎯</span>
              <span class="feature-text"><strong>Precise Matching:</strong> Gradually refine search conditions through conversation</span>
            </div>
          </div>
          
          <div class="example-grid">
            <button 
              v-for="example in examples" 
              :key="example" 
              @click="startSearch(example)"
              class="example-card"
            >
              {{ example }}
            </button>
          </div>
        </div>
      </div>

      <!-- Conversation History -->
      <div v-else class="conversations">
        <div 
          v-for="(conversation, index) in conversations" 
          :key="index" 
          class="conversation-item"
        >
          <!-- User Query -->
          <div class="user-query">
            <div class="query-content">
              <h3>{{ conversation.query }}</h3>
            </div>
          </div>

          <!-- AI Response -->
          <div class="ai-response">
            <div class="response-content">
              <!-- Loading State -->
              <div v-if="conversation.loading" class="loading-state">
                <div class="loading-spinner"></div>
                <span>Searching papers...</span>
              </div>

              <!-- Response Content -->
              <div v-else-if="conversation.response" class="response-text">
                <div v-html="formatResponse(conversation.response.message)"></div>
                
                <!-- Papers Section -->
                <div v-if="conversation.response.papers?.length > 0" class="papers-section">
                  <h4>📄 Related Papers ({{ conversation.response.papers.length }})</h4>
                  <div class="papers-grid">
                    <div 
                      v-for="paper in conversation.response.papers.slice(0, 6)" 
                      :key="paper.paper_id"
                      @click="openPaper(paper)"
                      class="paper-card"
                    >
                      <div class="paper-title">{{ paper.title }}</div>
                      <div class="paper-authors">{{ paper.authors }}</div>
                      <div class="paper-date">{{ formatDate(paper.published_date) }}</div>
                    </div>
                  </div>
                  
                  <!-- Show more papers button -->
                  <button 
                    v-if="conversation.response.papers.length > 6"
                    @click="showMorePapers(conversation)"
                    class="show-more-btn"
                  >
                    Show {{ conversation.response.papers.length - 6 }} more papers
                  </button>
                </div>

                <!-- Follow-up Questions -->
                <div v-if="conversation.response.suggestions?.length > 0" class="follow-up">
                  <h5>Continue exploring:</h5>
                  <div class="suggestions">
                    <button 
                      v-for="suggestion in conversation.response.suggestions.slice(0, 3)" 
                      :key="suggestion"
                      @click="startSearch(suggestion)"
                      class="suggestion-btn"
                    >
                      {{ suggestion }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Search Input (Fixed at bottom) -->
    <div class="search-input-container">
      <div class="search-input-wrapper">
        <div class="input-box">
          <textarea
            ref="searchInput"
            v-model="currentQuery"
            @keydown.enter.exact.prevent="handleSearch"
            @keydown.enter.shift.exact="addNewLine"
            :placeholder="inputPlaceholder"
            class="search-textarea"
            rows="1"
            :disabled="isSearching"
          ></textarea>
          <button 
            @click="handleSearch"
            :disabled="!currentQuery.trim() || isSearching"
            class="search-button"
          >
            <span v-if="isSearching" class="loading-icon">⏳</span>
            <span v-else class="search-icon">🔍</span>
          </button>
        </div>
        <div class="input-hint">
          Press Enter to search • Shift + Enter for new line
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import api from '../services/api'

// Reactive data
const conversations = ref([])
const currentQuery = ref('')
const isSearching = ref(false)
const searchInput = ref(null)

// Example queries
const examples = ref([
  "Find papers about latest transformer architectures",
  "Show me computer vision models for medical imaging", 
  "What are graph neural network applications?",
  "Find natural language processing papers in healthcare",
  "Search for reinforcement learning in robotics",
  "Show me federated learning privacy techniques"
])

// Computed
const inputPlaceholder = computed(() => {
  return conversations.value.length === 0 
    ? "Ask anything about research papers..."
    : "Ask a follow-up question..."
})

// Methods
const generateSessionId = () => {
  return 'perplexity_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
}

const startSearch = async (query) => {
  currentQuery.value = query
  await handleSearch()
}

const handleSearch = async () => {
  const query = currentQuery.value.trim()
  if (!query || isSearching.value) return

  // Create new conversation
  const conversation = {
    query,
    loading: true,
    response: null,
    sessionId: generateSessionId()
  }
  
  conversations.value.push(conversation)
  currentQuery.value = ''
  isSearching.value = true
  
  // Scroll to bottom
  await nextTick()
  scrollToBottom()

  try {
    // Build conversation history for context
    const conversationHistory = conversations.value.slice(0, -1).map(conv => ([
      { role: 'user', content: conv.query },
      { role: 'assistant', content: conv.response?.message || '' }
    ])).flat()

    // Call improved conversational search API
    const response = await api.improvedConversationalSearch({
      session_id: conversation.sessionId,
      query: query,
      conversation_history: conversationHistory
    })

    conversation.loading = false
    conversation.response = response

  } catch (error) {
    console.error('Search error:', error)
    conversation.loading = false
    conversation.response = {
      message: "Sorry, I encountered an error while searching. Please try again.",
      papers: [],
      suggestions: ["Try rephrasing your question", "Check your connection"]
    }
  } finally {
    isSearching.value = false
    await nextTick()
    scrollToBottom()
  }
}

const addNewLine = () => {
  currentQuery.value += '\n'
}

const formatResponse = (message) => {
  return message.replace(/\n/g, '<br>')
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short'
  })
}

const openPaper = (paper) => {
  const url = paper.pdf_url || `https://arxiv.org/abs/${paper.paper_id}`
  window.open(url, '_blank')
}

const showMorePapers = (conversation) => {
  // Could implement modal or expand inline
  console.log('Show more papers for:', conversation)
}

const scrollToBottom = () => {
  setTimeout(() => {
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: 'smooth'
    })
  }, 100)
}

onMounted(() => {
  if (searchInput.value) {
    searchInput.value.focus()
  }
})
</script>

<style scoped>
.perplexity-search {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Header removed */

/* Logo section removed */

/* Logo styles removed */

/* Tagline styles removed */

.main-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1rem 150px; /* Top padding added for spacing, bottom padding for fixed input */
}

/* Welcome State */
.welcome-state {
  padding: 2rem 0;
}

.welcome-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 3rem 2rem;
  text-align: center;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.welcome-card h2 {
  font-size: 2rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 0.5rem;
}

.welcome-card p {
  color: #718096;
  font-size: 1.1rem;
  margin: 0 0 1.5rem;
}

.feature-list {
  margin-bottom: 1.5rem;
  text-align: left;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.feature-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
  margin-top: 0.1rem;
}

.feature-text {
  color: #4a5568;
  font-size: 0.95rem;
  line-height: 1.4;
}

.feature-text strong {
  color: #2d3748;
}

.example-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
  margin-top: 2rem;
}

.example-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.95rem;
  color: #4a5568;
}

.example-card:hover {
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

/* Conversations */
.conversations {
  padding: 1rem 0;
}

.conversation-item {
  margin-bottom: 3rem;
}

.user-query {
  margin-bottom: 1.5rem;
}

.query-content {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 1.5rem;
  backdrop-filter: blur(10px);
}

.query-content h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #2d3748;
}

.ai-response {
  background: rgba(255, 255, 255, 0.98);
  border-radius: 16px;
  padding: 2rem;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #718096;
  font-size: 0.95rem;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #e2e8f0;
  border-top: 2px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.response-text {
  color: #2d3748;
  line-height: 1.6;
}

/* Papers Section */
.papers-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #e2e8f0;
}

.papers-section h4 {
  margin: 0 0 1.5rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: #2d3748;
}

.papers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 1rem;
}

.paper-card {
  background: #f7fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.paper-card:hover {
  border-color: #667eea;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.15);
}

.paper-title {
  font-weight: 600;
  color: #2d3748;
  font-size: 0.9rem;
  line-height: 1.4;
  margin-bottom: 0.5rem;
}

.paper-authors {
  color: #718096;
  font-size: 0.8rem;
  margin-bottom: 0.25rem;
}

.paper-date {
  color: #a0aec0;
  font-size: 0.75rem;
}

.show-more-btn {
  margin-top: 1rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.show-more-btn:hover {
  background: #5a67d8;
}

/* Follow-up */
.follow-up {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e2e8f0;
}

.follow-up h5 {
  margin: 0 0 1rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #4a5568;
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.suggestion-btn {
  background: #edf2f7;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  color: #4a5568;
  cursor: pointer;
  transition: all 0.2s ease;
}

.suggestion-btn:hover {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

/* Fixed Search Input */
.search-input-container {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  padding: 1.5rem;
}

.search-input-wrapper {
  max-width: 800px;
  margin: 0 auto;
}

.input-box {
  display: flex;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: border-color 0.2s ease;
}

.input-box:focus-within {
  border-color: #667eea;
}

.search-textarea {
  flex: 1;
  border: none;
  outline: none;
  padding: 1rem 1.25rem;
  font-size: 1rem;
  line-height: 1.5;
  resize: none;
  min-height: 48px;
  max-height: 120px;
  font-family: inherit;
}

.search-button {
  background: #667eea;
  border: none;
  padding: 0 1.25rem;
  cursor: pointer;
  transition: background-color 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-button:hover:not(:disabled) {
  background: #5a67d8;
}

.search-button:disabled {
  background: #cbd5e0;
  cursor: not-allowed;
}

.search-icon, .loading-icon {
  font-size: 1.2rem;
}

.input-hint {
  text-align: center;
  color: #718096;
  font-size: 0.8rem;
  margin-top: 0.75rem;
}

/* Responsive */
@media (max-width: 768px) {
  .logo {
    font-size: 2rem;
  }
  
  .welcome-card {
    padding: 2rem 1.5rem;
  }
  
  .example-grid {
    grid-template-columns: 1fr;
  }
  
  .papers-grid {
    grid-template-columns: 1fr;
  }
  
  .search-input-container {
    padding: 1rem;
  }
  
  .main-content {
    padding-bottom: 120px;
  }
}
</style>
