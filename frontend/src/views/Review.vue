<template>
  <div class="review-page">
    <div v-if="initialLoading" class="loading">Loading...</div>
    <div v-else class="full-layout">

      <RwsSidebar 
        :rws-sessions="rwsSessions"
        :current-session-id="currentSessionId"
        @create-session="createNewSession"
        @switch-session="switchSession"
        @delete-session="deleteThisSession"
      />

      <div class="two-panel-layout">
      <!-- Left Panel: File Upload & Papers Relation Graph -->
      <div class="left-panel">
        <div class="panel-header">
          <h3>Papers & Relations</h3>
        </div>
        
        <!-- File Upload Area -->
        <div class="file-upload-section">
          <div 
            class="file-drop-zone"
            :class="{ 'drag-over': isDragOver, 'has-files': uploadedFiles.length > 0 }"
            @drop="handleFileDrop"
            @dragover.prevent="isDragOver = true"
            @dragleave="isDragOver = false"
            @dragenter.prevent
            @click="triggerFileInput"
          >
            <div v-if="uploadedFiles.length === 0" class="drop-zone-content">
              <div class="drop-icon">📄</div>
              <p>Drag & drop files here</p>
              <p class="drop-hint">or click to browse files</p>
              <div class="supported-formats">Supports: PDF, DOC, DOCX, TXT</div>
            </div>
            <div v-else class="uploaded-files-preview">
              <div class="files-count">{{ uploadedFiles.length }} files uploaded</div>
              <button @click.stop="triggerFileInput" class="add-more-btn">+ Add More</button>
            </div>
          </div>
          
          <!-- Hidden File Input -->
          <input 
            ref="fileInputRef"
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.txt"
            @change="handleFileInput"
            style="display: none;"
          />
          
          <!-- Upload Progress -->
          <div v-if="uploadProgress.length > 0" class="upload-progress-section">
            <h5>Uploading Files...</h5>
            <div v-for="progress in uploadProgress" :key="progress.id" class="upload-item">
              <div class="upload-info">
                <span class="file-name">{{ progress.name }}</span>
                <span class="file-size">{{ formatFileSize(progress.size) }}</span>
              </div>
              <div class="progress-bar">
                <div 
                  class="progress-fill" 
                  :style="{ width: progress.progress + '%' }"
                  :class="{ 'completed': progress.progress === 100, 'error': progress.error }"
                ></div>
              </div>
              <div class="upload-status">
                <span v-if="progress.error" class="error-text">{{ progress.error }}</span>
                <span v-else-if="progress.progress === 100" class="success-text">✓ Complete</span>
                <span v-else class="progress-text">{{ progress.progress }}%</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Papers Relation Graph -->
        <div class="graph-section">
          <div class="graph-header">
            <h4>Papers Relation Graph</h4>
          </div>
          <div class="graph-container" ref="graphContainer">
            <div v-if="uploadedFiles.length === 0" class="graph-placeholder">
              <div class="placeholder-icon">🔗</div>
              <p>Upload files to see relations</p>
            </div>
            <div v-else class="graph-content">
              <!-- Simple Graph Visualization -->
              <svg class="relation-graph" :width="graphWidth" :height="graphHeight">
                <!-- Draw connections between papers -->
                <g class="connections">
                  <line 
                    v-for="connection in paperConnections" 
                    :key="`${connection.from}-${connection.to}`"
                    :x1="connection.x1" 
                    :y1="connection.y1"
                    :x2="connection.x2" 
                    :y2="connection.y2"
                    stroke="#90caf9" 
                    stroke-width="2"
                    opacity="0.6"
                  />
                </g>
                <!-- Draw paper nodes -->
                <g class="nodes">
                  <g 
                    v-for="(file, index) in uploadedFiles" 
                    :key="file.paper_id"
                    :transform="`translate(${file.x}, ${file.y})`"
                    class="paper-node"
                  >
                    <circle 
                      :r="30" 
                      fill="#2196f3" 
                      opacity="0.8"
                      stroke="#fff"
                      stroke-width="2"
                    />
                    <text 
                      text-anchor="middle" 
                      dy="5" 
                      fill="white" 
                      font-size="10"
                      font-weight="bold"
                    >
                      {{ index + 1 }}
                    </text>
                  </g>
                </g>
              </svg>
              
              <!-- Paper List -->
              <div class="paper-list">
                <div 
                  v-for="(file, index) in uploadedFiles" 
                  :key="file.paper_id"
                  class="paper-item"
                >
                  <span class="paper-number">{{ index + 1 }}</span>
                  <span class="paper-name">{{ file.filename }}</span>
                  <button 
                    @click="removeFile(file.paper_id)"
                    class="remove-btn"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Right Panel: Guidance Input & Generation -->
      <div class="right-panel">
        <div class="panel-header">
          <h3>Related Work Generation</h3>
        </div>
        
        <!-- Guidance Section -->
        <div class="guidance-section">
          <div class="guidance-messages" ref="guidanceContainer">
            <div v-for="guidance in guidanceList" :key="guidance.id" class="guidance-item">
              <div class="guidance-content">{{ guidance.content }}</div>
              <button @click="removeGuidance(guidance.id)" class="remove-guidance">×</button>
            </div>
            <div v-if="guidanceList.length === 0" class="guidance-placeholder">
              <p>Add guidance to help generate better related work sections</p>
            </div>
          </div>
        </div>
        
        <!-- Generated Result -->
        <div class="result-section">
          <div class="result-header">
            <h4>Generated Related Work</h4>
            <button 
              v-if="generatedContent"
              @click="copyToClipboard"
              class="copy-btn"
            >
              📋 Copy
            </button>
          </div>
          <div class="result-content" ref="resultContainer">
            <div v-if="!generatedContent && !isGenerating" class="result-placeholder">
              <p>Click "Generate" to create related work content</p>
            </div>
            <div v-else-if="isGenerating" class="generating-indicator">
              <div class="spinner"></div>
              <p>Generating related work...</p>
            </div>
            <div v-else class="generated-text" v-html="formatMessage(generatedContent)"></div>
          </div>
        </div>
        
        <!-- Input & Generate Section -->
        <div class="input-section">
          <div class="input-container">
            <textarea 
              ref="guidanceInputRef" 
              v-model="guidanceInputText"
              @keydown.enter.exact.prevent="addGuidance"
              placeholder="Extra guidance for related work generation..."
              class="guidance-input"
              rows="2"
            ></textarea>
            <button 
              @click="addGuidance"
              :disabled="!guidanceInputText.trim()"
              class="add-guidance-btn"
            >
              + Add
            </button>
          </div>
          
          <button 
            @click="generateRelatedWork"
            :disabled="uploadedFiles.length === 0 || isGenerating"
            class="generate-btn"
            :class="{ 'generating': isGenerating }"
          >
            <span v-if="isGenerating">⏳</span>
            <span v-else>Generate</span>
          </button>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick, computed } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';
import { chatSessionStore } from '../stores/chatSession';
import { rwsSessionStore } from '../stores/rwsSession';
import RwsSidebar from '../components/RwsSidebar.vue';
import api from '../services/api'

// UI refs
const initialLoading = ref(true);
const graphContainer = ref(null);
const guidanceContainer = ref(null);
const resultContainer = ref(null);
const guidanceInputRef = ref(null);
const fileInputRef = ref(null);

// File upload state
const uploadedFiles = ref([]);
const isDragOver = ref(false);
const isPaperProcessing = ref(false);
const uploadProgress = ref([]);

// Guidance state
const guidanceList = ref([]);
const guidanceInputText = ref('');

// Generation state
const generatedContent = ref('');
const isGenerating = ref(false);

// Graph state
const graphWidth = ref(400);
const graphHeight = ref(300);
const paperConnections = ref([]);

// Session management
const currentSessionId = ref(localStorage.getItem('currentRwsSessionId') || null);
const messages = ref([]);

// Computed properties
const rwsSessions = computed(() => rwsSessionStore.sessions || []);

// Watch paper processing state
watch(() => chatSessionStore.state.processingPaper, (isProcessing) => {
  isPaperProcessing.value = isProcessing;
}, { immediate: true });

onBeforeUnmount(() => {
  chatSessionStore.resetProcessingState();
});

// File handling functions
async function handleFileDrop(event) {
  event.preventDefault();
  isDragOver.value = false;
  
  const files = event.dataTransfer.files;
  if (files.length > 0) {
    await processFiles(files);
  } else {
    // Load existing files from the system if no files dropped
    await loadUserFiles();
  }
}

async function loadUserFiles() {
  try {
    const files = await api.get_user_files();
    uploadedFiles.value = files.map((file, index) => ({
      ...file,
      x: 50 + (index % 3) * 120,
      y: 50 + Math.floor(index / 3) * 80
    }));
    updatePaperConnections();
  } catch (error) {
    console.error('Failed to load user files:', error);
  }
}

function removeFile(paperId) {
  uploadedFiles.value = uploadedFiles.value.filter(file => file.paper_id !== paperId);
  updatePaperConnections();
}

function updatePaperConnections() {
  // Create simple connections between papers (for demo)
  const connections = [];
  for (let i = 0; i < uploadedFiles.value.length - 1; i++) {
    for (let j = i + 1; j < uploadedFiles.value.length; j++) {
      const file1 = uploadedFiles.value[i];
      const file2 = uploadedFiles.value[j];
      connections.push({
        from: file1.paper_id,
        to: file2.paper_id,
        x1: file1.x,
        y1: file1.y,
        x2: file2.x,
        y2: file2.y
      });
    }
  }
  paperConnections.value = connections;
}

// Guidance functions
function addGuidance() {
  if (!guidanceInputText.value.trim()) return;
  
  const guidance = {
    id: Date.now().toString(),
    content: guidanceInputText.value.trim()
  };
  
  guidanceList.value.push(guidance);
  guidanceInputText.value = '';
}

function removeGuidance(id) {
  guidanceList.value = guidanceList.value.filter(g => g.id !== id);
}

// Session management functions
async function switchSession(sessionId) {
  if (sessionId === currentSessionId.value) return;
  currentSessionId.value = sessionId;
  localStorage.setItem('currentRwsSessionId', sessionId); 
  initialLoading.value = true;
  await loadRwsSession(sessionId);
  initialLoading.value = false;
}

async function createNewSession() {
  currentSessionId.value = null;
  messages.value = [];
  generatedContent.value = '';
  guidanceList.value = [];
}

async function loadRwsSession(sessionId = null) {
  try {
    if (!sessionId) {
      messages.value = [];
      generatedContent.value = '';
      return;
    }
    
    const response = await api.get_rws_messages({ session_id: sessionId });
    messages.value = response || [];
    
    // Reconstruct the generated content from messages
    const lastAssistantMessage = messages.value.filter(m => m.role === 'assistant').pop();
    if (lastAssistantMessage) {
      generatedContent.value = lastAssistantMessage.content;
    } else {
      generatedContent.value = '';
    }
    
    await nextTick();
  } catch (error) {
    console.error('Failed to load RWS session:', error);
    messages.value = [];
    generatedContent.value = '';
  }
}

async function deleteThisSession(sessionId) {
  // if delete current session, just clear it
  if (sessionId === currentSessionId.value) {
    messages.value = [];
    generatedContent.value = '';
    guidanceList.value = [];
    currentSessionId.value = null;
    localStorage.removeItem('currentRwsSessionId');
  }

  try {
    await rwsSessionStore.deleteSession(sessionId);
  } catch (e) {
    console.error('failed to delete RWS session:', e);
  }
}

function extractTitleFromInput(input) {
  const trimmed = input.trim();
  if (!trimmed) return 'Untitled RWS Session';
  return trimmed.length > 50 ? trimmed.substring(0, 50) + '...' : trimmed;
}

// Generation function
async function generateRelatedWork() {
  if (uploadedFiles.value.length === 0 || isGenerating.value) return;
  
  // Create session if none exists
  if (!currentSessionId.value) {
    const guidanceText = guidanceList.value.length > 0 
      ? guidanceList.value.map(g => g.content).join(' ') 
      : '';
    const title = extractTitleFromInput(guidanceText || 'Related Work Generation');
    const newSession = await rwsSessionStore.createSession({ title });
    currentSessionId.value = newSession.id;
    localStorage.setItem('currentRwsSessionId', newSession.id);
  }
  
  isGenerating.value = true;
  generatedContent.value = '';
  
  try {
    // Prepare the guidance message
    const guidanceText = guidanceList.value.length > 0 
      ? `Please consider the following guidance:\n${guidanceList.value.map(g => `- ${g.content}`).join('\n')}\n\n`
      : '';
    
    const message = `${guidanceText}Generate a comprehensive related work section based on the ${uploadedFiles.value.length} uploaded papers. Focus on identifying key contributions, methodologies, and relationships between these works.`;
    
    // Get selected files
    const selectedFiles = uploadedFiles.value.map(file => file.paper_id);
    
    // Use the new RWS API with session support
    const response = await api.stream_rws({
      session_id: currentSessionId.value,
      message: message,
      selected_files: selectedFiles
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    // Process streaming response
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let accumulatedData = '';
    
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }
      
      const chunk = decoder.decode(value, { stream: true });
      accumulatedData += chunk;
      
      try {
        const lines = accumulatedData.split('\n');
        let remainingLines = [];
        
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          if (!line.trim()) continue;
          
          try {
            const jsonData = JSON.parse(line);
            if (jsonData.content) {
              generatedContent.value += jsonData.content;
            }
          } catch (e) {
            remainingLines.push(line);
          }
        }
        
        accumulatedData = remainingLines.join('\n');
        
        if (accumulatedData) {
          generatedContent.value += accumulatedData;
          accumulatedData = '';
        }
      } catch (e) {
        console.error('Error processing chunk:', e);
      }
      
      // Auto-scroll result container
      if (resultContainer.value) {
        resultContainer.value.scrollTop = resultContainer.value.scrollHeight;
      }
    }
  } catch (error) {
    console.error('Failed to generate related work:', error);
    generatedContent.value = "Failed to generate related work. Please try again.";
  } finally {
    isGenerating.value = false;
  }
}

// Utility functions
function formatMessage(content) {
  if (!content) return '';
  const html = marked(content);
  return DOMPurify.sanitize(html);
}

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(generatedContent.value);
    // You could add a toast notification here
    console.log('Content copied to clipboard');
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
  }
}

// Initialization
onMounted(async () => {
  try {
    initialLoading.value = true;
    
    // Initialize RWS sessions
    await rwsSessionStore.fetchAllSessions();
    const savedSessionId = localStorage.getItem('currentRwsSessionId');
    if (savedSessionId && rwsSessionStore.sessions.some(s => s.id === savedSessionId)) {
      currentSessionId.value = savedSessionId;
      await loadRwsSession(savedSessionId);
    } else {
      currentSessionId.value = null;
    }
    
    // Load existing files
    await loadUserFiles();
    
    initialLoading.value = false;
  } catch (err) {
    console.error('Initialization error:', err);
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

function triggerFileInput() {
  fileInputRef.value.click();
}

async function handleFileInput(event) {
  const files = event.target.files;
  if (files.length > 0) {
    await processFiles(files);
    // Reset the input so the same file can be selected again
    event.target.value = '';
  }
}

async function processFiles(fileList) {
  const files = Array.from(fileList);
  
  // Validate files
  const validFiles = files.filter(file => {
    const validTypes = ['application/pdf', 'application/msword', 
                       'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                       'text/plain'];
    const maxSize = 50 * 1024 * 1024; // 50MB
    
    if (!validTypes.includes(file.type)) {
      alert(`File "${file.name}" is not supported. Please upload PDF, DOC, DOCX, or TXT files.`);
      return false;
    }
    
    if (file.size > maxSize) {
      alert(`File "${file.name}" is too large. Maximum size is 50MB.`);
      return false;
    }
    
    return true;
  });
  
  if (validFiles.length === 0) return;
  
  // Process each valid file
  for (const file of validFiles) {
    await uploadFile(file);
  }
}

async function uploadFile(file) {
  const progressId = Date.now().toString() + Math.random().toString(36).substr(2, 9);
  
  // Add to progress tracking
  const progressItem = {
    id: progressId,
    name: file.name,
    size: file.size,
    progress: 0,
    error: null
  };
  
  uploadProgress.value.push(progressItem);
  
  try {
    // Simulate file upload progress
    for (let progress = 0; progress <= 100; progress += 10) {
      await new Promise(resolve => setTimeout(resolve, 100)); // Simulate upload time
      progressItem.progress = progress;
    }
    
    // Simulate successful upload - add to uploaded files
    const uploadedFile = {
      paper_id: progressId,
      filename: file.name,
      file_size: file.size,
      upload_date: new Date().toISOString(),
      x: 50 + (uploadedFiles.value.length % 3) * 120,
      y: 50 + Math.floor(uploadedFiles.value.length / 3) * 80,
      // Store file data for potential use
      fileData: file
    };
    
    uploadedFiles.value.push(uploadedFile);
    updatePaperConnections();
    
    // Remove from progress after a delay
    setTimeout(() => {
      uploadProgress.value = uploadProgress.value.filter(p => p.id !== progressId);
    }, 2000);
    
  } catch (error) {
    console.error('Upload error:', error);
    progressItem.error = 'Upload failed';
    
    // Remove failed upload after delay
    setTimeout(() => {
      uploadProgress.value = uploadProgress.value.filter(p => p.id !== progressId);
    }, 3000);
  }
}

function formatFileSize(size) {
  if (size < 1024) return size + ' B';
  if (size < 1024 * 1024) return (size / 1024).toFixed(2) + ' KB';
  if (size < 1024 * 1024 * 1024) return (size / (1024 * 1024)).toFixed(2) + ' MB';
  return (size / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
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
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 1.2rem;
  color: #666;
}

.full-layout {
  display: flex;
  height: 100%;
}

.two-panel-layout {
  display: flex;
  flex: 1;
  height: 100%;
  gap: 1rem;
  padding: 1rem;
}

/* Left Panel Styles */
.left-panel {
  flex: 0 0 45%;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 1.5rem;
  border-bottom: 1px solid #e0e0e0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 600;
}

.file-upload-section {
  padding: 1rem;
}

.file-drop-zone {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
  background: #fafafa;
}

.file-drop-zone.drag-over {
  border-color: #3f51b5;
  background-color: #f3f4ff;
}

.file-drop-zone.has-files {
  border-color: #4caf50;
  background-color: #f1f8e9;
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.drop-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.drop-hint {
  color: #666;
  font-size: 0.9rem;
}

.uploaded-files-preview {
  color: #4caf50;
  font-weight: 600;
}

.graph-section {
  flex: 1;
  padding: 1rem;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.graph-header h4 {
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1.1rem;
}

.graph-container {
  flex: 1;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.graph-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
}

.placeholder-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.graph-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.relation-graph {
  flex: 0 0 200px;
  background: #f9f9f9;
}

.paper-node {
  cursor: pointer;
}

.paper-list {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
}

.paper-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  background: #f5f5f5;
}

.paper-number {
  background: #2196f3;
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: bold;
}

.paper-name {
  flex: 1;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remove-btn {
  background: #f44336;
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  cursor: pointer;
  font-size: 0.8rem;
}

/* Right Panel Styles */
.right-panel {
  flex: 0 0 55%;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.guidance-section {
  padding: 1rem;
  border-bottom: 1px solid #e0e0e0;
  max-height: 150px;
}

.guidance-messages {
  max-height: 100px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.guidance-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #e3f2fd;
  border-radius: 6px;
  font-size: 0.9rem;
}

.guidance-content {
  flex: 1;
}

.remove-guidance {
  background: #666;
  color: white;
  border: none;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  cursor: pointer;
  font-size: 0.7rem;
}

.guidance-placeholder {
  color: #999;
  text-align: center;
  font-style: italic;
  padding: 1rem;
}

.result-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1rem 0.5rem 1rem;
}

.result-header h4 {
  margin: 0;
  color: #333;
  font-size: 1.1rem;
}

.copy-btn {
  background: #4caf50;
  color: white;
  border: none;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
}

.result-content {
  flex: 1;
  padding: 0 1rem 1rem 1rem;
  overflow-y: auto;
  border: 1px solid #e0e0e0;
  margin: 0 1rem;
  border-radius: 8px;
  background: #fafafa;
}

.result-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  font-style: italic;
}

.generating-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1rem;
  color: #666;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3f51b5;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.generated-text {
  padding: 1rem;
  line-height: 1.6;
  background: white;
  border-radius: 6px;
  margin: 1rem 0;
}

.input-section {
  padding: 1rem;
  border-top: 1px solid #e0e0e0;
  background: #f9f9f9;
}

.input-container {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.guidance-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.9rem;
  resize: vertical;
  min-height: 44px;
}

.guidance-input:focus {
  outline: none;
  border-color: #3f51b5;
}

.add-guidance-btn {
  background: #2196f3;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  white-space: nowrap;
}

.add-guidance-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.generate-btn {
  width: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 1rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.1rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.generate-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.generate-btn.generating {
  background: #ff9800;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.add-more-btn {
  background: #2196f3;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  white-space: nowrap;
}

.upload-progress-section {
  padding: 1rem;
  border-top: 1px solid #e0e0e0;
  background: #f9f9f9;
}

.upload-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: white;
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.upload-info {
  flex: 1;
}

.file-name {
  font-size: 0.9rem;
}

.file-size {
  font-size: 0.8rem;
  color: #666;
}

.progress-bar {
  flex: 1;
  height: 10px;
  background: #f0f0f0;
  border-radius: 5px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #4caf50;
  transition: width 0.3s ease;
}

.progress-fill.completed {
  background: #4caf50;
}

.progress-fill.error {
  background: #f44336;
}

.upload-status {
  font-size: 0.8rem;
  color: #666;
}

.error-text {
  color: #f44336;
}

.success-text {
  color: #4caf50;
}

.progress-text {
  color: #666;
}

.supported-formats {
  font-size: 0.8rem;
  color: #888;
  margin-top: 0.5rem;
  padding: 0.3rem 0.6rem;
  background: #f0f8ff;
  border-radius: 4px;
  border: 1px solid #e3f2fd;
}
</style>

<style>
body {
  --app-max-width: none !important;
  overflow-x: hidden;
}
</style>