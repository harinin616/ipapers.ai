<template>
  <div class="chat-page" :style="chatPageStyle">
    <div v-if="initialLoading" class="loading">Loading...</div>
    <div v-else class="full-layout">

      <ChatSidebar 
        :chat-sessions="chatSessions"
        :current-session-id="currentSessionId"
        @create-session="createNewSession"
        @switch-session="switchSession"
        @delete-session="deleteThisSession"
      />

      <!-- Chat Area -->
      <div class="chat-view">
        <!-- Chat content loading state -->
        <div v-if="chatLoading" class="chat-content-loading">
          <div class="chat-loader"></div>
          <div>Loading chat...</div>
        </div>
        
        <!-- Normal chat content -->
        <div v-else class="chat-section">
          <div class="chat-header">
            <div class="header-main">
              <h2>iPapers Chat</h2>
               <p class="header-subtitle">
                Ask anything about the papers from the File List
              </p>
            </div>
          </div>

          <div class="chat-container">
            <div class="chat-messages" ref="messagesContainer">
              <div v-for="message in messages" :key="message.id"
                   :class="[
                     'chat-message', 
                     message.role === 'user' ? 'user-message' : 'assistant-message',
                     message.role === 'assistant' && isTyping && message.id === currentTypingMessageId ? 'typing' : ''
                   ]"
                   :data-message-id="message.id">
                <div class="message-content" v-html="formatMessage(message.content)" :class="{ 'live-typing': message.role === 'assistant' && isTyping && message.id === currentTypingMessageId }"></div>
              </div>
              <div v-if="isLoading && messages.length === 0" class="chat-loading">
                <div class="chat-loader"></div>
                <div>AI is thinking...</div>
              </div>
            </div>
            <div class="chat-input-container">
              <div class="chat-input-wrapper" 
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
                  class="chat-input"
                ></textarea>
              </div>
              <button 
                @click="sendMessage" 
                :disabled="isLoading || !userInput.trim() || isPaperProcessing"
                class="chat-send-button"
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
import ChatSidebar from '../components/ChatSidebar.vue'


// Chat data
const user_id = ref("");
const messages = ref([]);
const userInput = ref('');
const isLoading = ref(false);  // Message loading status
const initialLoading = ref(true);  // Initial loading status
const chatLoading = ref(false);  // Chat content loading status for session switching
const isTyping = ref(false);
const currentTypingMessageId = ref(null); // Current typing message ID
const messagesContainer = ref(null);
const inputField = ref(null);

// check if paper is processing
const isPaperProcessing = ref(false);

// Header height calculation
const headerHeight = ref(60); // Default fallback

// Dynamic height calculation for chat page
const chatPageStyle = computed(() => ({
  height: `calc(100vh - ${headerHeight.value}px)`
}));

// Function to get actual header height
const getHeaderHeight = () => {
  const header = document.querySelector('.app-header');
  if (header) {
    headerHeight.value = header.offsetHeight;
  }
};

// watch paper processing state
watch(() => chatSessionStore.state.processingPaper, (isProcessing) => {
  isPaperProcessing.value = isProcessing;
}, { immediate: true });

// Clean up on unmount
onBeforeUnmount(() => {
  chatSessionStore.resetProcessingState();
  // Restore body overflow when leaving chat
  document.body.style.overflowY = '';
  document.documentElement.style.overflowY = '';
  // Remove resize listener
  window.removeEventListener('resize', getHeaderHeight);
});

// input placeholder
const inputPlaceholder = computed(() => {
  return 'Type your message...';
});

const chatSessions = computed(() => chatSessionStore.sessions || []);

const currentSessionId = ref(localStorage.getItem('currentSessionId') || null);


async function switchSession(sessionId) {
  if (sessionId === currentSessionId.value) return;
  currentSessionId.value = sessionId;
  localStorage.setItem('currentSessionId', sessionId); 
  chatLoading.value = true;
  await loadChatSession(sessionId);
  chatLoading.value = false;
}

// just clear the current session, create new session when sending message
async function createNewSession() {
  currentSessionId.value = null;
  messages.value = [];
}

async function loadChatSession(sessionId=null) {
  try {
    isLoading.value = true;
    const response = await api.get_messages({ session_id: sessionId });
    messages.value = response || [];
    await nextTick();
    scrollToBottom();
  } catch (error) {
    console.error('Failed to load session:', error);
    messages.value = [];
  } finally {
    isLoading.value = false;
  }
}

async function deleteThisSession(sessionId) {
  // if delete current session, just clear it
  if (sessionId === currentSessionId.value) {
    messages.value = [];
    currentSessionId.value = null;
    localStorage.removeItem('currentSessionId');
  }

  try {
    await chatSessionStore.deleteSession(sessionId);

  } catch (e) {
    console.error('failed to delete session:', e);
  }
}



// Initialization
onMounted(async () => {
  try {
    // Hide body overflow to prevent outer scrollbar
    document.body.style.overflowY = 'hidden';
    document.documentElement.style.overflowY = 'hidden';
    
    // Get actual header height
    getHeaderHeight();
    
    // Listen for window resize to update header height
    window.addEventListener('resize', getHeaderHeight);
    
    await chatSessionStore.fetchAllSessions();
    const savedSessionId = localStorage.getItem('currentSessionId');
    if (savedSessionId && chatSessionStore.sessions.some(s => s.id === savedSessionId)) {
      currentSessionId.value = savedSessionId;
      await loadChatSession(savedSessionId);
    }
    else {
      currentSessionId.value = null
    }

    initialLoading.value = true;
    
    user_id.value = localStorage.getItem('X-User-ID');

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

function extractTitleFromInput(input) {
  const trimmed = input.trim();
  if (!trimmed) return 'Untitled Session';
  return trimmed;
}

// Send message or execute search
async function sendMessage() {
  // if input is empty or loading or processing, return
  if (!userInput.value.trim() || isLoading.value) return;
  
  // check if paper is processing
  if (isPaperProcessing.value) {
    return;
  }
  if (!currentSessionId.value) {
    const newSession = await chatSessionStore.createSession({ title: null});
    currentSessionId.value = newSession.id;
    localStorage.setItem('currentSessionId', newSession.id); 
  }
  
  const messageContent = userInput.value.trim();
  userInput.value = '';
  const session = chatSessions.value?.find(s => s.id === currentSessionId.value);
  if (session && (!session.title || !session.title.trim())) {
    const newTitle = extractTitleFromInput(messageContent);
    await api.update_session_title({ session_id: currentSessionId.value, title: newTitle });
    session.title = newTitle;
  }
  // Add user message to UI
  const userMessage = {
    id: Date.now().toString(),
    role: 'user',
    content: messageContent,
    created_at: new Date().toISOString()
  };
  
  messages.value.push(userMessage);
  
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
    messages.value.push(assistantMessage);
    const now = Date.now();
    const session = chatSessions.value?.find(s => s.id === currentSessionId.value);
    if (session) {
      session.lastMessageAt = now;
  // 重新排序
      chatSessions.value?.sort((a, b) => (b.lastMessageAt || 0) - (a.lastMessageAt || 0));
    }
    await streamChatResponse(messageContent, assistantMessage);

  } catch (err) {
    console.error('Failed to send message:', err);
    if (messages.value.length > 0 && 
        messages.value[messages.value.length - 1].role === 'assistant' && 
        messages.value[messages.value.length - 1].content === '') {
      messages.value.pop();
    }

  } finally {
    isLoading.value = false;
    isTyping.value = false;
    currentTypingMessageId.value = null;
  }
}

import { fileSelectionStore } from '@/stores/fileSelectionStore';


// Stream chat response
async function streamChatResponse(userMessage, assistantMessage) {
  try {
    // Send request
    const response = await api.stream_chat({
    session_id:    currentSessionId.value,
    message:       userMessage,
    selected_files: fileSelectionStore.getSelectedFiles(), 
  });
    
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

// Modify formatMessage function, simplify processing to avoid complex caching
function formatMessage(content) {
  if (!content) return '';
  const html = marked(content);
  return DOMPurify.sanitize(html);
}

// Scroll to bottom
function scrollToBottom() {
  if (messagesContainer.value) {
    // Use requestAnimationFrame to ensure browser has rendered the latest content
    window.requestAnimationFrame(() => {
         if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
      }
    });
  }
}

// Improve watch to ensure scroll updates when messages change
watch(
  () => messages.value.map(m => m.content),
  () => {
    nextTick(() => {
      scrollToBottom();
    });
  },
  { deep: true }
);
</script>

<style scoped>
.chat-page {
  width: 100%;
  /* height: calc(100vh - 60px); */ /* Remove fixed height calculation */
  position: relative;
  display: flex;
  flex-direction: column;
  background-color: var(--surface-2);
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

.loading{
  text-align: center;
  padding: 2rem;
  background-color: var(--surface);
  border-radius: 8px;
  box-shadow: var(--shadow-1);
  margin-bottom: 2rem;
}

.chat-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  background-color: var(--surface);
  border-radius: 0;
  box-shadow: none;
}

.chat-section {
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100%;
  overflow: hidden;
  padding: 1rem;
}

.chat-header {
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
.header-main {
  flex-direction: column;    /* stack children vertically */
  align-items: flex-start;   /* left-align them */
  gap: 4px;                  /* optional spacing between h2 and p */
}

.header-main h2 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--text);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: var(--surface-2);
  border-radius: 8px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.chat-message {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  position: relative;
  line-height: 1.5;
  display: flex;
  align-items: flex-start;
  margin-bottom: 0.5rem;
}

.chat-message.user-message {
  align-self: flex-end;
  background-color: var(--accent-soft);
  color: #0d47a1;
  border-bottom-right-radius: 2px;
}

.chat-message.assistant-message {
  align-self: flex-start;
  background-color: var(--surface);
  color: var(--text);
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

.chat-input-container {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  border-top: 1px solid var(--border);
  background-color: var(--surface);
  border-radius: 0 0 8px 8px;
  gap: 0.5rem;
}

.chat-input-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  border: 1px solid var(--border);
  border-radius: 24px;
  background-color: var(--surface);
  transition: all 0.2s;
  overflow: hidden;
  padding: 0.5rem 1rem 0;
}

.chat-input-wrapper:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(63, 81, 181, 0.2);
}

.chat-input {
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

.chat-send-button {
  background-color: var(--accent);
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

.chat-send-button:hover:not(:disabled) {
  background-color: var(--brand-600);
  transform: translateY(-1px);
}

.chat-send-button:disabled {
  background-color: #bdbdbd;
  cursor: not-allowed;
}

.chat-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-2);
  font-style: italic;
  padding: 0.5rem;
}

.chat-content-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1rem;
  color: var(--text-2);
  font-size: 0.95rem;
}

.chat-loader {
  width: 20px;
  height: 20px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.chat-input:disabled {
  background-color: var(--surface-2);
  color: #6c757d;
  cursor: not-allowed;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chat-input-wrapper.processing-mode {
  border-color: #ffb74d;
  background-color: #fff8e1;
}

.chat-input-wrapper.processing-mode .chat-input {
  background-color: transparent;
}

.chat-input-wrapper.processing-mode::after {
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

.header-subtitle {
  white-space: pre-line; /* 保留文本中的换行 */
  margin: 0;
  font-size: 1rem;
  color: var(--text-2);
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
  /* overflow-x: hidden; */ /* Remove as we now control via JavaScript */
}
</style> 