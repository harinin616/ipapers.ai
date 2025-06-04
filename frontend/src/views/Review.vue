<template>
  <div class="review-page">
    <div v-if="initialLoading" class="loading">Loading...</div>
    <div v-else class="full-layout">
      <!-- Review Area -->
      <div class="review-view">
        <div class="review-section">
          <div class="review-header">
            <div class="header-main">
              <h2>Review</h2>
            </div>
            <!-- Button Controls -->
            <div class="review-controls">
              <button 
                @click="setActiveView('comparison')"
                :class="['control-button', { 'active': activeView === 'comparison' }]"
              >
                Comparison
              </button>
              <button 
                @click="setActiveView('relatedWork')"
                :class="['control-button', { 'active': activeView === 'relatedWork' }]"
              >
                Related Work Generation
              </button>
            </div>
          </div>

          <div class="review-container">
            <div class="review-messages" ref="messagesContainer">
              <div v-for="message in currentMessages" :key="message.id" 
                   :class="[
                     'review-message', 
                     message.role === 'user' ? 'user-message' : 'assistant-message',
                     message.role === 'assistant' && isTyping && message.id === currentTypingMessageId ? 'typing' : ''
                   ]"
                   :data-message-id="message.id">
                <div class="message-content" v-html="formatMessage(message.content)" :class="{ 'live-typing': message.role === 'assistant' && isTyping && message.id === currentTypingMessageId }"></div>
              </div>
              <div v-if="isLoading && currentMessages.length === 0" class="review-loading">
                <div class="review-loader"></div>
                <div>AI is thinking...</div>
              </div>
            </div>
            <div class="review-input-container">
              <div class="review-input-wrapper" 
                :class="{ 
                  'processing-mode': isLoading || isPaperProcessing
                }"
              >
                <textarea 
                  ref="inputField" 
                  v-model="userInput"
                  @keydown.enter.exact.prevent="sendMessage"
                  :placeholder="inputPlaceholder"
                  :disabled="false"
                  class="review-input"
                ></textarea>
              </div>
              <button 
                @click="sendMessage" 
                :disabled="isLoading || !userInput.trim() || isPaperProcessing"
                class="review-send-button"
              >
                <span v-if="isLoading">⏳</span>
                <span v-else-if="isPaperProcessing">⌛</span>
                <span v-else>Send</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, computed, nextTick } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';
import { chatSessionStore } from '../stores/chatSession';
import api from '../services/api'

// Review data
const user_id = ref("");
const initialLoading = ref(true);
const activeView = ref('comparison'); // Default to comparison view
const messagesContainer = ref(null);
const inputField = ref(null);

// Messages for each view
const comparisonMessages = ref([]);
const relatedWorkMessages = ref([]);

// Chat functionality
const userInput = ref('');
const isLoading = ref(false);
const isTyping = ref(false);
const currentTypingMessageId = ref(null);

// check if paper is processing
const isPaperProcessing = ref(false);

// watch paper processing state
watch(() => chatSessionStore.state.processingPaper, (isProcessing) => {
  isPaperProcessing.value = isProcessing;
}, { immediate: true });

onBeforeUnmount(() => {
  chatSessionStore.resetProcessingState();
});

// Get current messages based on active view
const currentMessages = computed(() => {
  return activeView.value === 'comparison' ? comparisonMessages.value : relatedWorkMessages.value;
});

// input placeholder
const inputPlaceholder = computed(() => {
  if (activeView.value === 'comparison') {
    return 'Ask about paper comparison...';
  } else {
    return 'Ask about related work generation...';
  }
});

// Set active view
function setActiveView(view) {
  activeView.value = view;
  console.log(`Switched to ${view} view`);
  // Scroll to bottom when switching views
  nextTick(() => {
    scrollToBottom();
  });
}

// Send message
async function sendMessage() {
  // if input is empty or loading or processing, return
  if (!userInput.value.trim() || isLoading.value) return;
  
  // check if paper is processing
  if (isPaperProcessing.value) {
    return;
  }
  
  const messageContent = userInput.value.trim();
  userInput.value = '';
  
  // Add user message to current view's messages
  const userMessage = {
    id: Date.now().toString(),
    role: 'user',
    content: messageContent,
    created_at: new Date().toISOString()
  };
  
  if (activeView.value === 'comparison') {
    comparisonMessages.value.push(userMessage);
  } else {
    relatedWorkMessages.value.push(userMessage);
  }
  
  // Scroll to bottom
  await nextTick();
  scrollToBottom();
  
  // Start processing reply
  try {
    isLoading.value = true;
    isTyping.value = true;
    
    // Add an empty assistant message as placeholder
    const assistantMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString()
    };
    
    currentTypingMessageId.value = assistantMessage.id;
    
    if (activeView.value === 'comparison') {
      comparisonMessages.value.push(assistantMessage);
    } else {
      relatedWorkMessages.value.push(assistantMessage);
    }
    
    await streamResponse(messageContent, assistantMessage);
  } catch (err) {
    console.error('Failed to send message:', err);
    // Remove empty assistant message on error
    const currentMsgs = activeView.value === 'comparison' ? comparisonMessages.value : relatedWorkMessages.value;
    if (currentMsgs.length > 0 && 
        currentMsgs[currentMsgs.length - 1].role === 'assistant' && 
        currentMsgs[currentMsgs.length - 1].content === '') {
      currentMsgs.pop();
    }
  } finally {
    isLoading.value = false;
    isTyping.value = false;
    currentTypingMessageId.value = null;
  }
}

// Stream response (different endpoint based on view)
async function streamResponse(userMessage, assistantMessage) {
  try {
    // Use different API endpoint based on active view
    let response;
    if (activeView.value === 'comparison') {
      response = await api.chat_comparison(userMessage);
    } else {
      response = await api.chat_rwg(userMessage);
    }
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    // Process streaming response
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let receivedChunks = 0;
    let accumulatedData = '';
    
    // Message container reference - for direct DOM manipulation
    const messageEl = document.querySelector(`[data-message-id="${assistantMessage.id}"]`);
    
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        isTyping.value = false;
        scrollToBottom();
        break;
      }
      
      // Decode data
      const chunk = decoder.decode(value, { stream: true });
      receivedChunks++;
      
      // Add new chunk to accumulated data
      accumulatedData += chunk;
      
      try {
        // Try to parse JSON lines
        const lines = accumulatedData.split('\n');
        let remainingLines = [];
        
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          if (!line.trim()) continue;
          
          try {
            // Try to parse as JSON
            const jsonData = JSON.parse(line);
            // If successfully parsed, add to message content
            if (jsonData.content) {
              assistantMessage.content += jsonData.content;
              updateMessageDisplay(messageEl, assistantMessage.content);
            }
          } catch (e) {
            // If this line is not complete JSON, keep for next processing
            remainingLines.push(line);
          }
        }
        
        // Update accumulated data, only keeping unparsed parts
        accumulatedData = remainingLines.join('\n');
        
        // If there's remaining plain text data, directly add to message
        if (accumulatedData) {
          assistantMessage.content += accumulatedData;
          updateMessageDisplay(messageEl, assistantMessage.content);
          accumulatedData = '';
        }
      } catch (e) {
        console.error('Error processing chunk:', e);
      }
    }
  } catch (error) {
    console.error('Failed to get streaming response:', error);
    assistantMessage.content = "Failed to get response. Please try again.";
    throw error;
  }
}

// Helper function to update message display
function updateMessageDisplay(messageEl, content) {
  if (messageEl) {
    // Create temporary div to parse HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = DOMPurify.sanitize(marked(content));
    
    // Get content container and update
    const contentEl = messageEl.querySelector('.message-content');
    if (contentEl) {
      contentEl.innerHTML = tempDiv.innerHTML;
    }
  }
  
  // Scroll to bottom
  scrollToBottom();
}

// Format message using markdown
function formatMessage(content) {
  if (!content) return '';
  const html = marked(content);
  return DOMPurify.sanitize(html);
}

// Scroll to bottom
function scrollToBottom() {
  if (messagesContainer.value) {
    window.requestAnimationFrame(() => {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    });
  }
}

// Watch for message changes to auto-scroll
watch(
  () => [comparisonMessages.value.map(m => m.content), relatedWorkMessages.value.map(m => m.content)],
  () => {
    nextTick(() => {
      scrollToBottom();
    });
  },
  { deep: true }
);

// Initialization
onMounted(async () => {
  try {
    initialLoading.value = true;
    
    user_id.value = localStorage.getItem('X-User-ID');

    // Load review data for both views
    await loadReviewData();
    
    initialLoading.value = false;
  } catch (err) {
    console.error('Initialization error:', err);
    if (err.response) {
      console.error('API response:', err.response.status, err.response.data);
    } else if (err.request) {
      console.error('No response received:', err.request);
    } else {
      console.error('Error message:', err.message);
    }
    initialLoading.value = false;
  }
  
  // Setup highlighting
  marked.setOptions({
    highlight: function(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value;
      }
      return hljs.highlightAuto(code).value;
    }
  });
});

// Load review data (placeholder for future implementation)
async function loadReviewData() {
  try {
    // This will be implemented later to load saved messages for each view
    console.log('Loading review data...');
    
    await nextTick();
    scrollToBottom();
  } catch (error) {
    console.error('Failed to load review data:');
  }
}
</script>

<style scoped>
.review-page {
  width: 100%;
  height: calc(100vh - 60px);
  position: relative;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
  overflow: hidden;
}

.full-layout {
  display: flex;
  height: 100%;
  width: 100%;
  overflow: visible;
  margin: 0;
  padding: 12px;
  box-sizing: border-box;
  transition: all 0.3s ease;
}

.loading {
  text-align: center;
  padding: 2rem;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.review-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  max-width: 100%;
  padding: 0;
  overflow: hidden;
  height: 100%;
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.review-section {
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100%;
  overflow: hidden;
  padding: 1rem;
}

.review-header {
  display: flex;
  flex-direction: column;
  padding-bottom: 0.75rem;
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.header-main h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.review-controls {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.control-button {
  padding: 0.75rem 1.5rem;
  border: 2px solid #e0e0e0;
  background-color: #fff;
  color: #666;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
  flex: 1;
  text-align: center;
}

.control-button:hover {
  border-color: #3f51b5;
  color: #3f51b5;
  background-color: #f8f9ff;
}

.control-button.active {
  background-color: #3f51b5;
  color: white;
  border-color: #3f51b5;
  box-shadow: 0 2px 4px rgba(63, 81, 181, 0.2);
}

.control-button.active:hover {
  background-color: #303f9f;
  border-color: #303f9f;
}

.review-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.review-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.review-message {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  position: relative;
  line-height: 1.5;
  display: flex;
  align-items: flex-start;
  margin-bottom: 0.5rem;
}

.review-message.user-message {
  align-self: flex-end;
  background-color: #e3f2fd;
  color: #0d47a1;
  border-bottom-right-radius: 2px;
}

.review-message.assistant-message {
  align-self: flex-start;
  background-color: #fff;
  color: #333;
  border-bottom-left-radius: 2px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.message-content {
  overflow-wrap: break-word;
  word-wrap: break-word;
  word-break: break-word;
  font-size: 0.95rem;
}

.message-content p {
  margin: 0 0 0.75rem;
}

.message-content p:last-child {
  margin-bottom: 0;
}

.review-input-container {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  border-top: 1px solid #eee;
  background-color: white;
  border-radius: 0 0 8px 8px;
  gap: 0.5rem;
}

.review-input-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  border: 1px solid #ddd;
  border-radius: 24px;
  background-color: #fff;
  transition: all 0.2s;
  overflow: hidden;
  padding: 0.5rem 1rem 0;
}

.review-input-wrapper:focus-within {
  border-color: #3f51b5;
  box-shadow: 0 0 0 2px rgba(63, 81, 181, 0.2);
}

.review-input {
  width: 100%;
  min-height: 44px;
  max-height: 120px;
  padding: 0.25rem 0;
  border: none;
  outline: none;
  resize: none;
  font-family: inherit;
  font-size: 0.95rem;
  line-height: 1.4;
  overflow-y: auto;
  background-color: transparent;
}

.review-send-button {
  background-color: #3f51b5;
  color: white;
  border: none;
  border-radius: 50%;
  min-width: 44px;
  height: 44px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: 0 14px;
}

.review-send-button:hover:not(:disabled) {
  background-color: #303f9f;
  transform: translateY(-1px);
}

.review-send-button:disabled {
  background-color: #bdbdbd;
  cursor: not-allowed;
}

.review-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #666;
  font-style: italic;
  padding: 0.5rem;
}

.review-loader {
  width: 20px;
  height: 20px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #3f51b5;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.review-input:disabled {
  background-color: #f8f9fa;
  color: #6c757d;
  cursor: not-allowed;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.review-input-wrapper.processing-mode {
  border-color: #ffb74d;
  background-color: #fff8e1;
}

.review-input-wrapper.processing-mode .review-input {
  background-color: transparent;
}

.review-input-wrapper.processing-mode::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  background-color: #ff9800;
  animation: processing-bar 2s infinite linear;
  width: 100%;
  transform: scaleX(0);
  transform-origin: 0 0;
}

@keyframes processing-bar {
  0% {
    transform: scaleX(0);
  }
  50% {
    transform: scaleX(1);
  }
  100% {
    transform: scaleX(0);
    transform-origin: 100% 0;
  }
}
</style>

<style>
body {
  --app-max-width: none !important;
  overflow-x: hidden;
}
</style>