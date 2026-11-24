<template>
  <div class="grant-search">
    <div class="search-container">
      <div class="search-header">
        <h2>Grant Search Assistant</h2>
        <p>Ask me about grants and funding opportunities. I can help you find specific grants or answer questions!</p>
      </div>
      
      <!-- Chat Messages -->
      <div class="chat-container">
        <div class="messages" ref="messagesContainer">
          <div 
            v-for="(message, index) in messages" 
            :key="index"
            :class="['message', message.role]"
          >
            <div class="message-content">
              <div v-if="message.role === 'assistant'" class="message-text">
                <div v-html="formatMessage(message.content)"></div>
                
                <!-- Show grants if available -->
                <div v-if="message.grants && message.grants.length > 0" class="grants-preview">
                  <h4>Found {{ message.grants.length }} grants:</h4>
                  <div class="grants-list">
                    <div 
                      v-for="grant in message.grants.slice(0, 3)" 
                      :key="grant.grant_id"
                      class="grant-item"
                    >
                      <h5>{{ grant.title }}</h5>
                      <p class="grant-agency">{{ grant.agency }}</p>
                      <p class="grant-synopsis">{{ grant.synopsis?.substring(0, 150) }}...</p>
                      <a :href="grant.detail_url" target="_blank" class="grant-link">View Details</a>
                    </div>
                  </div>
                  <button 
                    v-if="message.grants.length > 3"
                    @click="showAllResults = !showAllResults"
                    class="show-more-btn"
                  >
                    {{ showAllResults ? 'Show Less' : `Show All ${message.grants.length} Grants` }}
                  </button>
                  <div v-if="showAllResults" class="results-container">
                    <div class="grants-list">
                      <div 
                        v-for="grant in message.grants"
                        :key="grant.grant_id + '_full'"
                        class="grant-card"
                      >
                        <div class="grant-header">
                          <h4 class="grant-title">{{ grant.title }}</h4>
                          <span class="grant-status" :class="(grant.status || '').toLowerCase()">{{ grant.status }}</span>
                        </div>
                        <div class="grant-details">
                          <div v-if="grant.agency"><strong>Agency:</strong> {{ grant.agency }}</div>
                          <div class="grant-synopsis">{{ grant.synopsis }}</div>
                          <div class="grant-dates">
                            <div v-if="grant.posted_date"><strong>Posted:</strong> {{ formatDate(grant.posted_date) }}</div>
                            <div v-if="grant.close_date"><strong>Close:</strong> {{ formatDate(grant.close_date) }}</div>
                          </div>
                        </div>
                        <div class="grant-actions">
                          <a :href="grant.detail_url" target="_blank" class="view-grant-button">View on Grants.gov</a>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- Show suggestions if available -->
                <div v-if="message.suggestions && message.suggestions.length > 0" class="suggestions">
                  <h4>You might also want to ask:</h4>
                  <div class="suggestion-tags">
                    <span 
                      v-for="suggestion in message.suggestions" 
                      :key="suggestion"
                      @click="selectSuggestion(suggestion)"
                      class="suggestion-tag"
                    >
                      {{ suggestion }}
                    </span>
                  </div>
                </div>
              </div>
              <div v-else class="message-text">
                {{ message.content }}
              </div>
            </div>
          </div>
          
          <!-- Loading indicator -->
          <div v-if="isLoading" class="message assistant">
            <div class="message-content">
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Input Area -->
      <div class="input-container">
        <div class="input-wrapper">
          <input
            v-model="searchQuery"
            @keyup.enter="sendMessage"
            placeholder="Ask me about grants (e.g., 'Find education grants', 'What grants are available for small businesses?')"
            class="search-input"
            :disabled="isLoading"
          />
          <button 
            @click="sendMessage" 
            class="send-button"
            :disabled="isLoading || !searchQuery.trim()"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22,2 15,22 11,13 2,9 22,2"></polygon>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import apiService from '@/services/api'

const searchQuery = ref('')
const searchResults = ref([])
const suggestions = ref([])
const isLoading = ref(false)
const errorMessage = ref('')
const conversationHistory = ref([])
const messages = ref([])
const showAllResults = ref(false)
const messagesContainer = ref<HTMLElement>()

const sendMessage = async () => {
  if (!searchQuery.value.trim()) return
  
  const userMessage = searchQuery.value.trim()
  searchQuery.value = ''
  
  // Add user message to chat
  messages.value.push({
    role: 'user',
    content: userMessage,
    timestamp: new Date().toISOString()
  })
  
  isLoading.value = true
  errorMessage.value = ''
  
  try {
    const response = await apiService.improvedGrantSearch({
      session_id: 'grant-search-session',
      query: userMessage,
      conversation_history: conversationHistory.value
    })
    
    // Add assistant response to chat
    messages.value.push({
      role: 'assistant',
      content: response.message,
      grants: response.grants || [],
      suggestions: response.suggestions || [],
      timestamp: new Date().toISOString()
    })
    
    // Update conversation history
    conversationHistory.value.push({
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    })
    conversationHistory.value.push({
      role: 'assistant',
      content: response.message,
      grants: response.grants,
      timestamp: new Date().toISOString()
    })
    
    // Update search results if grants found
    if (response.grants && response.grants.length > 0) {
      searchResults.value = response.grants
    }
    
    // Scroll to bottom
    await nextTick()
    scrollToBottom()
    
  } catch (error) {
    console.error('Grant search error:', error)
    messages.value.push({
      role: 'assistant',
      content: 'Sorry, there was an error processing your request. Please try again.',
      timestamp: new Date().toISOString()
    })
  } finally {
    isLoading.value = false
  }
}

const selectSuggestion = (suggestion: string) => {
  searchQuery.value = suggestion
  sendMessage()
}

const formatMessage = (content: string) => {
  // Simple formatting for bold text and line breaks
  return content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const formatDate = (dateString: string) => {
  if (!dateString) return ''
  try {
    return new Date(dateString).toLocaleDateString()
  } catch {
    return dateString
  }
}

onMounted(() => {
  // Add welcome message
  messages.value.push({
    role: 'assistant',
    content: 'Hello! I\'m your grant search assistant. I can help you find government grants and funding opportunities. What would you like to search for?',
    suggestions: [
      'Find education grants',
      'Show me research funding',
      'What grants are available for small businesses?',
      'Find healthcare grants',
      'Search for environmental funding'
    ],
    timestamp: new Date().toISOString()
  })
})
</script>

<style scoped>
.grant-search {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  height: calc(100vh - 40px);
  display: flex;
  flex-direction: column;
}

.search-container {
  background: var(--surface-2);
  border-radius: 8px;
  padding: 30px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.search-header h2 {
  margin: 0 0 10px 0;
  color: var(--text);
}

.search-header p {
  margin: 0 0 20px 0;
  color: #6c757d;
}

.chat-container {
  flex: 1;
  min-height: 0;
  margin-bottom: 20px;
}

.messages {
  height: 100%;
  overflow-y: auto;
  padding: 20px;
  background: var(--surface);
  border-radius: 8px;
  border: 1px solid var(--border);
}

.message {
  margin-bottom: 20px;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 18px;
  word-wrap: break-word;
}

.message.user .message-content {
  background: #007bff;
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  background: #f1f3f4;
  color: var(--text);
  border-bottom-left-radius: 4px;
}

.message-text {
  line-height: 1.4;
}

.grants-preview {
  margin-top: 15px;
  padding: 15px;
  background: var(--surface-2);
  border-radius: 8px;
  border: 1px solid var(--border);
}

.grants-preview h4 {
  margin: 0 0 10px 0;
  color: var(--text);
}

.grants-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.grant-item {
  padding: 10px;
  background: var(--surface);
  border-radius: 6px;
  border: 1px solid var(--border);
}

.grant-item h5 {
  margin: 0 0 5px 0;
  color: var(--text);
  font-size: 14px;
}

.grant-agency {
  margin: 0 0 5px 0;
  color: #6c757d;
  font-size: 12px;
  font-weight: 500;
}

.grant-synopsis {
  margin: 0 0 8px 0;
  color: var(--text-2);
  font-size: 12px;
  line-height: 1.3;
}

.grant-link {
  color: #007bff;
  text-decoration: none;
  font-size: 12px;
  font-weight: 500;
}

.grant-link:hover {
  text-decoration: underline;
}

.show-more-btn {
  margin-top: 10px;
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.show-more-btn:hover {
  background: #0056b3;
}

.suggestions {
  margin-top: 15px;
}

.suggestions h4 {
  margin: 0 0 10px 0;
  color: var(--text);
  font-size: 14px;
}

.suggestion-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.suggestion-tag {
  padding: 6px 12px;
  background: var(--border);
  color: #495057;
  border-radius: 16px;
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.suggestion-tag:hover {
  background: #007bff;
  color: white;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  align-items: center;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #6c757d;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
}

.input-container {
  margin-top: auto;
}

.input-wrapper {
  display: flex;
  gap: 10px;
  align-items: center;
}

.search-input {
  flex: 1;
  padding: 12px 16px;
  border: 2px solid var(--border);
  border-radius: 24px;
  font-size: 16px;
  transition: border-color 0.3s;
}

.search-input:focus {
  outline: none;
  border-color: #007bff;
}

.send-button {
  padding: 12px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: background-color 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-button:hover:not(:disabled) {
  background: #0056b3;
}

.send-button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.suggestions h4 {
  margin: 0 0 10px 0;
  color: #495057;
}

.suggestion-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.suggestion-tag {
  background: var(--border);
  color: #495057;
  padding: 6px 12px;
  border-radius: 20px;
  cursor: pointer;
  transition: background-color 0.3s;
  font-size: 14px;
}

.suggestion-tag:hover {
  background: var(--border);
}

.results-container {
  margin-top: 30px;
}

.results-header {
  margin-bottom: 20px;
}

.results-header h3 {
  margin: 0 0 5px 0;
  color: var(--text);
}

.results-header p {
  margin: 0;
  color: #6c757d;
}

.grants-list {
  display: grid;
  gap: 20px;
}

.grant-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: box-shadow 0.3s;
}

.grant-card:hover {
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.grant-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
}

.grant-title {
  margin: 0;
  color: var(--text);
  font-size: 18px;
  line-height: 1.4;
  flex: 1;
  margin-right: 15px;
}

.grant-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
  text-transform: uppercase;
}

.grant-status.posted {
  background: #d4edda;
  color: #155724;
}

.grant-status.forecast {
  background: #fff3cd;
  color: #856404;
}

.grant-details {
  margin-bottom: 15px;
}

.grant-details > div {
  margin-bottom: 8px;
}

.grant-synopsis {
  line-height: 1.5;
  color: #495057;
}

.grant-dates {
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: #6c757d;
}

.grant-categories {
  margin-top: 10px;
}

.category-tag {
  display: inline-block;
  background: var(--surface-2);
  color: #495057;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 12px;
  margin-right: 6px;
  margin-top: 4px;
}

.grant-actions {
  text-align: right;
}

.view-grant-button {
  background: #28a745;
  color: white;
  padding: 8px 16px;
  border-radius: 4px;
  text-decoration: none;
  font-size: 14px;
  transition: background-color 0.3s;
}

.view-grant-button:hover {
  background: #218838;
  color: white;
}

.error-message {
  background: #f8d7da;
  color: #721c24;
  padding: 15px;
  border-radius: 6px;
  margin-top: 20px;
}

.loading {
  text-align: center;
  padding: 40px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
