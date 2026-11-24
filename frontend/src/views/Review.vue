<template>
  <div class="review-page" :style="reviewPageStyle">
    <div v-if="initialLoading" class="loading">Loading...</div>
    <div v-else class="full-layout">

      <RwsSidebar 
        ref="rwsSidebarRef"
        :rws-sessions="rwsSessions"
        :current-session-id="currentSessionId"
        @create-session="createNewSession"
        @switch-session="switchSession"
        @delete-session="deleteThisSession"
      />

      <div class="two-panel-layout" :class="{ 'sidebar-collapsed': isSidebarCollapsed }">
              <!-- Left Panel: File Upload & Papers Relation Graph -->
        <div class="left-panel">
          <div class="panel-header">
            <h3>Papers & Relations</h3>
          </div>
          
          <!-- File Upload Area -->
          <div class="file-upload-section">
            <div class="upload-buttons-container">
              <!-- Upload Own Files Button -->
              <div 
                class="upload-button upload-own-files"
                :class="{ 'drag-over': isDragOver }"
                @drop="handleFileDrop"
                @dragover.prevent="isDragOver = true"
                @dragleave="isDragOver = false"
                @dragenter.prevent
                @click="triggerFileInput"
              >
                <div class="upload-icon">📄</div>
                <div class="upload-text">Upload Own Files</div>
              </div>
              
              <!-- Add from Filelist Button -->
              <div class="upload-button add-from-list" @click="openFileSelectionDialog">
                <div class="upload-icon">📁</div>
                <div class="upload-text">Add from File List</div>
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
            <div class="graph-controls" v-if="uploadedFiles.length > 1">
              <button 
                v-if="!isChoosingTarget"
                @click="startChoosingTarget" 
                class="choose-target-btn"
                :class="{ 'has-target': targetPaper }"
                title="Choose target paper (missing related work section)"
              >
                <span v-if="targetPaper">🎯 Target: {{ getShortFilename(targetPaper) }}</span>
                <span v-else>🎯 Choose Target</span>
              </button>
              <button 
                v-if="targetPaper && !isChoosingTarget"
                @click="clearTargetPaper" 
                class="clear-target-btn"
                title="Clear selected target paper"
              >
                ✕ Clear Target
              </button>
              <button 
                v-else-if="isChoosingTarget" 
                @click="cancelChoosingTarget" 
                class="cancel-target-btn"
                title="Cancel choosing target"
              >
                Cancel Target
              </button>
              <button 
                v-if="!isAddingEdge && !isChoosingTarget" 
                @click="startAddingEdge" 
                class="add-edge-btn"
                title="Add relationship between papers"
              >
                + Add Edge
              </button>
              <button 
                v-else-if="isAddingEdge"
                @click="cancelAddingEdge" 
                class="cancel-edge-btn"
                title="Cancel adding edge"
              >
                Cancel
              </button>
              <button 
                v-if="uploadedFiles.length > 2 && !isAddingEdge && !isChoosingTarget"
                @click="regenerateLayout" 
                class="regenerate-btn"
                title="Regenerate graph layout"
              >
                🔄 Rearrange
              </button>
            </div>
          </div>
          <div class="graph-container" ref="graphContainer">
            <div v-if="uploadedFiles.length === 0" class="graph-placeholder">
              <div class="placeholder-icon">🔗</div>
              <p>Upload files to see relations</p>
            </div>
            <div v-else class="graph-content">
              <!-- Graph Visualization with Directed Edges -->
              <svg class="relation-graph" :width="graphWidth" :height="graphHeight">
                <!-- Arrow marker definition -->
                <defs>
                  <marker id="arrowhead" markerWidth="8" markerHeight="6" 
                          refX="8" refY="3" orient="auto">
                    <polygon points="0 0, 8 3, 0 6" fill="url(#edgeGradient)" />
                  </marker>
                  
                  <!-- Gradients for nodes -->
                  <linearGradient id="nodeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#42a5f5" />
                    <stop offset="50%" stop-color="#1e88e5" />
                    <stop offset="100%" stop-color="#1565c0" />
                  </linearGradient>
                  
                  <linearGradient id="selectedGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#ffb74d" />
                    <stop offset="50%" stop-color="#ff9800" />
                    <stop offset="100%" stop-color="#f57c00" />
                  </linearGradient>
                  
                  <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stop-color="#42a5f5" stop-opacity="0.6" />
                    <stop offset="70%" stop-color="#1e88e5" stop-opacity="0.3" />
                    <stop offset="100%" stop-color="#1565c0" stop-opacity="0.1" />
                  </radialGradient>
                  
                  <radialGradient id="selectedGlow" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stop-color="#ffb74d" stop-opacity="0.6" />
                    <stop offset="70%" stop-color="#ff9800" stop-opacity="0.3" />
                    <stop offset="100%" stop-color="#f57c00" stop-opacity="0.1" />
                  </radialGradient>
                  
                  <linearGradient id="targetGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#e91e63" />
                    <stop offset="50%" stop-color="#c2185b" />
                    <stop offset="100%" stop-color="#ad1457" />
                  </linearGradient>
                  
                  <radialGradient id="targetGlow" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stop-color="#e91e63" stop-opacity="0.6" />
                    <stop offset="70%" stop-color="#c2185b" stop-opacity="0.3" />
                    <stop offset="100%" stop-color="#ad1457" stop-opacity="0.1" />
                  </radialGradient>
                  
                  <!-- Gradients for edges -->
                  <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#4caf50" />
                    <stop offset="50%" stop-color="#66bb6a" />
                    <stop offset="100%" stop-color="#4caf50" />
                  </linearGradient>
                  
                  <!-- Gradient for delete button -->
                  <linearGradient id="deleteGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#f44336" />
                    <stop offset="50%" stop-color="#e53935" />
                    <stop offset="100%" stop-color="#d32f2f" />
                  </linearGradient>
                </defs>
                <!-- Draw directed connections between papers -->
                <g class="connections">
                  <g v-for="connection in paperConnections" :key="`${connection.from}-${connection.to}`">
                    <!-- Glow effect -->
                    <path 
                      :d="connection.path"
                      stroke="url(#edgeGradient)" 
                      stroke-width="6"
                      fill="none"
                      opacity="0.3"
                      marker-end="url(#arrowhead)"
                      class="edge-glow"
                    />
                    <!-- Main edge -->
                    <path 
                      :d="connection.path"
                      stroke="url(#edgeGradient)" 
                      stroke-width="3"
                      fill="none"
                      opacity="0.9"
                      marker-end="url(#arrowhead)"
                      class="edge-main"
                    />
                    <!-- Edge label background -->
                    <rect 
                      :x="connection.labelX - 35" 
                      :y="connection.labelY - 12"
                      width="70"
                      height="20"
                      rx="12"
                      ry="12"
                      fill="rgba(255,255,255,0.95)"
                      stroke="url(#edgeGradient)"
                      stroke-width="1.5"
                      class="edge-label-bg"
                    />
                    <!-- Edge label -->
                    <text 
                      :x="connection.labelX" 
                      :y="connection.labelY + 2"
                      text-anchor="middle" 
                      font-size="10" 
                      fill="#2d3748"
                      class="edge-label"
                      font-weight="600"
                    >
                      {{ connection.relationship_type }}
                    </text>
                    <!-- Remove edge button with improved styling -->
                    <circle 
                      :cx="connection.labelX + 45" 
                      :cy="connection.labelY"
                      r="10"
                      fill="url(#deleteGradient)"
                      class="remove-edge-btn"
                      @click="removeEdge(connection.from, connection.to)"
                      style="cursor: pointer;"
                    />
                    <text 
                      :x="connection.labelX + 45" 
                      :y="connection.labelY + 3"
                      text-anchor="middle" 
                      font-size="12" 
                      fill="white"
                      style="pointer-events: none;"
                      font-weight="bold"
                    >
                      ×
                    </text>
                  </g>
                </g>
                <!-- Draw paper nodes -->
                <g class="nodes">
                  <g 
                    v-for="(file, index) in uploadedFiles" 
                    :key="file.paper_id"
                    :transform="`translate(${file.x}, ${file.y})`"
                    class="paper-node"
                    @click="selectPaper(file.paper_id)"
                    :class="{ 
                      'adding-edge': isAddingEdge,
                      'choosing-target': isChoosingTarget,
                      'selected': selectedFromPaper === file.paper_id,
                      'target-paper': targetPaper === file.paper_id
                    }"
                  >
                    <!-- Outer glow -->
                    <circle 
                      :r="28" 
                      :fill="getNodeGlow(file.paper_id)" 
                      opacity="0.3"
                      class="node-glow"
                    />
                    <!-- Main node -->
                    <circle 
                      :r="24" 
                      :fill="getNodeFill(file.paper_id)" 
                      stroke="rgba(255,255,255,0.8)"
                      stroke-width="3"
                      class="node-main"
                    />
                    <!-- Inner highlight -->
                    <circle 
                      :r="18" 
                      fill="none"
                      stroke="rgba(255,255,255,0.4)"
                      stroke-width="1"
                      class="node-highlight"
                    />
                    <!-- Number background -->
                    <circle 
                      :r="12" 
                      fill="rgba(255,255,255,0.9)"
                      class="number-bg"
                    />
                    <text 
                      text-anchor="middle" 
                      dy="4" 
                      :fill="selectedFromPaper === file.paper_id ? '#ff6f00' : '#1565c0'" 
                      font-size="12"
                      font-weight="700"
                      class="node-number"
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
        

        
        <!-- Generated Result -->
        <div class="result-section">
          <div class="result-header">
            <h4>Generated Related Work</h4>
            <button 
              v-if="rwsMessages.length > 0"
              @click="copyLastAssistantMessage"
              class="copy-btn"
            >
              📋 Copy
            </button>
          </div>
          <div class="result-content" ref="resultContainer">
            <div v-if="rwsMessages.length === 0 && !isGenerating" class="result-placeholder">
              <p>Click "Generate" to create related work content</p>
            </div>
            <div v-else class="rws-messages">
              <div v-for="message in rwsMessages" :key="message.id"
                   :class="[
                     'rws-message', 
                     message.role === 'user' ? 'user-message' : 'assistant-message',
                     message.role === 'assistant' && isGenerating && message.id === currentGeneratingMessageId ? 'generating' : ''
                   ]">
                <div class="message-content" v-html="formatMessage(message.content)"></div>
              </div>
              <div v-if="isGenerating && rwsMessages.length === 0" class="generating-indicator">
                <div class="spinner"></div>
                <p>Generating related work...</p>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Input & Generate Section -->
        <div class="input-section">
          <div class="input-container">
            <textarea 
              ref="guidanceInputRef" 
              v-model="guidanceInputText"
              @keydown.enter.exact.prevent="generateRelatedWork"
              placeholder="Extra guidance for related work generation..."
              class="guidance-input"
              rows="2"
            ></textarea>
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
    
    <!-- Edge Edit Dialog -->
    <div v-if="edgeEditDialog" class="dialog-overlay" @click="edgeEditDialog = false">
      <div class="dialog-content" @click.stop>
        <h3>Add Paper Relationship</h3>
        <div class="dialog-field">
          <label>From:</label>
          <span>{{ uploadedFiles.find(f => f.paper_id === currentEdge.from)?.filename || 'Paper' }}</span>
        </div>
        <div class="dialog-field">
          <label>To:</label>
          <span>{{ uploadedFiles.find(f => f.paper_id === currentEdge.to)?.filename || 'Paper' }}</span>
        </div>
        <div class="dialog-field">
          <label for="relationship-type">Relationship Type:</label>
          <select id="relationship-type" v-model="currentEdge.relationship_type">
            <option value="relates_to">relates to</option>
            <option value="builds_on">builds on</option>
            <option value="compares_to">compares to</option>
            <option value="contradicts">contradicts</option>
          </select>
        </div>
        <div class="dialog-field">
          <label for="relationship-desc">Description (optional):</label>
          <textarea 
            id="relationship-desc" 
            v-model="currentEdge.description" 
            placeholder="Describe the relationship..."
            rows="3"
          ></textarea>
        </div>
        <div class="dialog-actions">
          <button @click="edgeEditDialog = false" class="cancel-btn">Cancel</button>
          <button @click="saveEdge" class="save-btn">Save</button>
        </div>
      </div>
    </div>

    <!-- File Selection Dialog -->
    <div v-if="fileSelectionDialog" class="dialog-overlay" @click="fileSelectionDialog = false">
      <div class="dialog-content file-selection-dialog" @click.stop>
        <h3>Add from File List</h3>
        <div class="dialog-field">
          <div v-if="loadingGlobalFiles" class="loading-files">
            <div class="spinner"></div>
            <p>Loading files...</p>
          </div>
          <div v-else-if="globalFileList.length === 0" class="no-files">
            <p>No files available in your File List.</p>
            <!-- <p class="hint">Upload files in the Chat section first to add them here.</p> -->
          </div>
          <div v-else class="file-list">
            <div class="file-list-header">
              <label>
                <input 
                  type="checkbox" 
                  @change="toggleSelectAll"
                  :checked="selectedGlobalFiles.length === globalFileList.length"
                  :indeterminate="selectedGlobalFiles.length > 0 && selectedGlobalFiles.length < globalFileList.length"
                />
                Select All ({{ selectedGlobalFiles.length }}/{{ globalFileList.length }})
              </label>
            </div>
            <div class="file-items">
              <div 
                v-for="file in globalFileList" 
                :key="file.paper_id"
                class="file-item"
                :class="{ 'already-added': isFileAlreadyAdded(file.paper_id) }"
              >
                <label class="file-item-label">
                  <input 
                    type="checkbox" 
                    :value="file.paper_id"
                    v-model="selectedGlobalFiles"
                    :disabled="isFileAlreadyAdded(file.paper_id)"
                  />
                  <div class="file-info">
                    <div class="file-name">{{ file.filename }}</div>
                    <div class="file-meta">
                      <span class="file-date">{{ formatDate(file.added_at) }}</span>
                      <span v-if="isFileAlreadyAdded(file.paper_id)" class="already-added-label">Already in session</span>
                    </div>
                  </div>
                </label>
              </div>
            </div>
          </div>
        </div>
        <div class="dialog-actions">
          <button @click="fileSelectionDialog = false" class="cancel-btn">Cancel</button>
          <button 
            @click="addSelectedFiles" 
            class="save-btn"
            :disabled="selectedGlobalFiles.length === 0"
          >
            Add {{ selectedGlobalFiles.length }} Files
          </button>
        </div>
      </div>
    </div>


    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, onActivated, watch, nextTick, computed } from 'vue';
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
const rwsSidebarRef = ref(null);

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
const rwsMessages = ref([]);
const currentGeneratingMessageId = ref(null);

// Graph state
const graphWidth = ref(400);
const graphHeight = ref(250);
const paperConnections = ref([]);
const paperGraph = ref({ nodes: [], edges: [] });
const isAddingEdge = ref(false);
const selectedFromPaper = ref(null);
const edgeEditDialog = ref(false);
const currentEdge = ref({ from: '', to: '', relationship_type: 'relates_to', description: '' });
const isCompletingGraph = ref(false);

// Target paper state
const isChoosingTarget = ref(false);
const targetPaper = ref(null);

// File selection dialog state
const fileSelectionDialog = ref(false);
const globalFileList = ref([]);
const selectedGlobalFiles = ref([]);
const loadingGlobalFiles = ref(false);

// Session management
const currentSessionId = ref(localStorage.getItem('currentRwsSessionId') || null);
const messages = ref([]);

// Layout state
const isSidebarCollapsed = ref(false);
let resizeObserver = null;

// Header height calculation
const headerHeight = ref(60); // Default fallback

// Dynamic height calculation for review page
const reviewPageStyle = computed(() => ({
  height: `calc(100vh - ${headerHeight.value}px)`
}));

// Function to get actual header height
const getHeaderHeight = () => {
  const header = document.querySelector('.app-header');
  if (header) {
    headerHeight.value = header.offsetHeight;
  }
};

// Computed properties
const rwsSessions = computed(() => rwsSessionStore.sessions || []);

// Watch paper processing state
watch(() => chatSessionStore.state.processingPaper, (isProcessing) => {
  isPaperProcessing.value = isProcessing;
}, { immediate: true });

// Watch sidebar collapse state
watch(() => rwsSidebarRef.value?.isCollapsed, (collapsed) => {
  isSidebarCollapsed.value = collapsed;
  // Update graph visualization when sidebar state changes
  nextTick(() => {
    updateGraphVisualization();
  });
}, { immediate: true });

// Watch guidance text changes and save to session storage
watch(() => guidanceInputText.value, (newGuidance) => {
  if (currentSessionId.value) {
    saveSessionState();
  }
});

// Note: Removed watches for paperConnections and generatedContent
// as they are now managed by the backend and don't need localStorage persistence



onBeforeUnmount(() => {
  // Save current session state before unmounting
  if (currentSessionId.value) {
    saveSessionState();
  }
  
  chatSessionStore.resetProcessingState();
  
  // Clean up resize observer
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
  
  // Restore body overflow when leaving review
  document.body.style.overflowY = '';
  document.documentElement.style.overflowY = '';
  // Remove resize listener
  window.removeEventListener('resize', getHeaderHeight);
});

// When component is activated (e.g., switching back from chat), ensure graph is rendered and session is restored
onActivated(() => {
  nextTick(() => {
    updateGraphVisualization();
    
    // If we have a current session but no messages loaded, reload the session
    if (currentSessionId.value && messages.value.length === 0) {
      loadRwsSession(currentSessionId.value);
    }
  });
});

// File handling functions
async function handleFileDrop(event) {
  event.preventDefault();
  isDragOver.value = false;
  
  const files = event.dataTransfer.files;
  if (files.length > 0) {
    await processFiles(files);
  }
  // Note: Removed automatic loading of user files - sessions should be isolated
}

// Note: Removed loadUserFiles() function - sessions should be isolated
// Files are only loaded per-session via loadRwsSession() -> get_rws_session_files()

async function removeFile(paperId) {
  try {
    // Remove from backend session first if we have a current session
    if (currentSessionId.value) {
      await api.remove_rws_session_file(currentSessionId.value, paperId);
    }
    
    // Remove from local state after successful backend removal
    uploadedFiles.value = uploadedFiles.value.filter(file => file.paper_id !== paperId);
    
    // Update graph nodes to reflect the change
    if (currentSessionId.value) {
      await updateGraphNodes();
    }
    
    // Update graph visualization after removing file
    nextTick(() => {
      updateGraphVisualization();
    });
  } catch (error) {
    console.error('Failed to remove file:', error);
    // If backend removal failed, reload session files to ensure consistency
    if (currentSessionId.value) {
      try {
        const sessionFiles = await api.get_rws_session_files(currentSessionId.value);
        uploadedFiles.value = sessionFiles.map((file, index) => ({
          ...file,
          x: 50 + (index % 3) * 120,
          y: 50 + Math.floor(index / 3) * 80
        }));
        await updateGraphNodes();
        nextTick(() => {
          updateGraphVisualization();
        });
      } catch (reloadError) {
        console.error('Failed to reload session files after remove error:', reloadError);
      }
    }
  }
}
  


// Session state persistence functions
function saveSessionState() {
  if (!currentSessionId.value) return;
  
  // Only save guidance text if it's not empty (user is actively typing)
  // Don't save empty guidance as it means it was already used or cleared
  const sessionState = {
    guidanceText: guidanceInputText.value.trim() || '', // Save only if there's actual content
    targetPaper: targetPaper.value,
    lastUpdated: Date.now()
  };
  
  localStorage.setItem(`rws_session_state_${currentSessionId.value}`, JSON.stringify(sessionState));
}

function loadSessionState() {
  if (!currentSessionId.value) return;
  
  try {
    const stateData = localStorage.getItem(`rws_session_state_${currentSessionId.value}`);
    if (stateData) {
      const sessionState = JSON.parse(stateData);
      
      // Restore guidance text
      if (sessionState.guidanceText) {
        guidanceInputText.value = sessionState.guidanceText;
      }
      
      // Restore target paper
      if (sessionState.targetPaper) {
        targetPaper.value = sessionState.targetPaper;
      }
      
      // Restore generated content if it exists
      if (sessionState.generatedContent) {
        generatedContent.value = sessionState.generatedContent;
      }
      
      // Restore RWS messages if they exist
      if (sessionState.rwsMessages && Array.isArray(sessionState.rwsMessages)) {
        rwsMessages.value = sessionState.rwsMessages;
      }
    }
  } catch (error) {
    console.error('Failed to load session state:', error);
  }
}

function loadSessionStateWithoutMessages() {
  if (!currentSessionId.value) return;
  
  try {
    const stateData = localStorage.getItem(`rws_session_state_${currentSessionId.value}`);
    if (stateData) {
      const sessionState = JSON.parse(stateData);
      
      // Only restore guidance text if it's not empty (indicates unfinished user input)
      // Empty guidance means it was already used or cleared after generation
      if (sessionState.guidanceText && sessionState.guidanceText.trim()) {
        guidanceInputText.value = sessionState.guidanceText.trim();
      } else {
        guidanceInputText.value = '';
      }
      
      // Restore target paper
      if (sessionState.targetPaper) {
        targetPaper.value = sessionState.targetPaper;
      }
      
      // Note: We don't restore rwsMessages or generatedContent here
      // as they come from the backend messages
    }
  } catch (error) {
    console.error('Failed to load session state:', error);
  }
}

function clearSessionState(sessionId) {
  localStorage.removeItem(`rws_session_state_${sessionId}`);
}

// Session management functions
async function switchSession(sessionId) {
  if (sessionId === currentSessionId.value) return;
  
  // Save current session state before switching
  if (currentSessionId.value) {
    saveSessionState();
  }
  
  // Clear current state to prevent bleed-through
  messages.value = [];
  generatedContent.value = '';
  guidanceInputText.value = '';
  rwsMessages.value = [];
  uploadedFiles.value = [];
  paperConnections.value = [];
  paperGraph.value = { nodes: [], edges: [] };
  targetPaper.value = null;
  
  currentSessionId.value = sessionId;
  localStorage.setItem('currentRwsSessionId', sessionId); 
  initialLoading.value = true;
  await loadRwsSession(sessionId);
  initialLoading.value = false;
}

async function createNewSession() {
  // Save current session state before creating new session
  if (currentSessionId.value) {
    saveSessionState();
  }
  
  // Create a new RWS session
  try {
    const newSession = await rwsSessionStore.createSession({ title: 'New RWS Session' });
    currentSessionId.value = newSession.id;
    localStorage.setItem('currentRwsSessionId', newSession.id);
    messages.value = [];
    generatedContent.value = '';
    guidanceInputText.value = '';
    rwsMessages.value = [];
    uploadedFiles.value = [];
    paperConnections.value = [];
    paperGraph.value = { nodes: [], edges: [] };
    targetPaper.value = null;
  } catch (error) {
    console.error('Failed to create new RWS session:', error);
  }
}

async function loadRwsSession(sessionId = null) {
  try {
    if (!sessionId) {
      messages.value = [];
      generatedContent.value = '';
      guidanceList.value = [];
      uploadedFiles.value = [];
      return;
    }
    
    // Clear all current state first to ensure clean session loading
    messages.value = [];
    generatedContent.value = '';
    guidanceInputText.value = '';
    rwsMessages.value = [];
    uploadedFiles.value = [];
    paperConnections.value = [];
    paperGraph.value = { nodes: [], edges: [] };
    targetPaper.value = null;
    
    // Load messages from backend
    const response = await api.get_rws_messages({ session_id: sessionId });
    messages.value = response || [];
    
    // Convert backend messages to frontend format for rwsMessages
    if (messages.value.length > 0) {
      rwsMessages.value = messages.value
        .filter((msg) => {
          // Filter out user messages that don't have display_content (auto-generated prompts)
          if (msg.role === 'user' && !msg.display_content) {
            return false;
          }
          return true;
        })
        .map((msg, index) => ({
          id: `${sessionId}_${index}_${msg.timestamp || Date.now()}`,
          role: msg.role,
          // Use display_content for user messages if available, otherwise use content
          content: msg.role === 'user' && msg.display_content ? msg.display_content : msg.content,
          created_at: msg.timestamp ? new Date(msg.timestamp * 1000).toISOString() : new Date().toISOString()
        }));
    }
    
    // Load session files
    try {
      const sessionFiles = await api.get_rws_session_files(sessionId);
      uploadedFiles.value = sessionFiles.map((file, index) => ({
        ...file,
        x: 50 + (index % 3) * 120,
        y: 50 + Math.floor(index / 3) * 80
      }));
      
      // Update graph nodes and load paper graph
      await updateGraphNodes();
      await loadPaperGraph();
      await nextTick();
      updateGraphVisualization();
    } catch (fileError) {
      console.error('Failed to load session files:', fileError);
      uploadedFiles.value = [];
    }
    
    // Load session state (guidance text) but not rwsMessages since we loaded from backend
    loadSessionStateWithoutMessages();
    
    // Load target paper from backend
    try {
      const targetResponse = await api.get_target_paper(sessionId);
      targetPaper.value = targetResponse.target_paper_id;
    } catch (targetError) {
      console.error('Failed to load target paper:', targetError);
      targetPaper.value = null;
    }
    
    // If no messages from backend or localStorage, keep rwsMessages empty
    // The backend messages take precedence over localStorage for conversation history
    
    // Note: Guidance is now handled separately in the backend, 
    // so we no longer need to extract it from user messages
    
    await nextTick();
  } catch (error) {
    console.error('Failed to load RWS session:', error);
    messages.value = [];
    generatedContent.value = '';
    guidanceInputText.value = '';
    rwsMessages.value = [];
    uploadedFiles.value = [];
  }
}

async function deleteThisSession(sessionId) {
  // Clear the session state from localStorage
  clearSessionState(sessionId);
  
  // if delete current session, just clear it
  if (sessionId === currentSessionId.value) {
    messages.value = [];
    generatedContent.value = '';
    guidanceInputText.value = '';
    rwsMessages.value = [];
    uploadedFiles.value = [];
    paperConnections.value = [];
    paperGraph.value = { nodes: [], edges: [] };
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

function generateTitleFromFiles(files) {
  if (!files || files.length === 0) return 'Untitled RWS Session';
  
  if (files.length === 1) {
    // Single file: use paper title if available, otherwise filename
    const file = files[0];
    if (file.title && file.title.trim()) {
      return `RWS: ${file.title.length > 40 ? file.title.substring(0, 40) + '...' : file.title}`;
    } else if (file.filename) {
      const nameWithoutExt = file.filename.replace(/\.[^/.]+$/, "");
      return `RWS: ${nameWithoutExt.length > 40 ? nameWithoutExt.substring(0, 40) + '...' : nameWithoutExt}`;
    }
  } else {
    // Multiple files: create a descriptive title
    const firstFile = files[0];
    if (firstFile.title && firstFile.title.trim()) {
      const shortTitle = firstFile.title.length > 25 ? firstFile.title.substring(0, 25) + '...' : firstFile.title;
      return `RWS: ${shortTitle} + ${files.length - 1} more`;
    } else {
      return `RWS: ${files.length} Papers`;
    }
  }
  
  return 'Untitled RWS Session';
}

async function updateSessionTitleAfterFileChange() {
  // Only update if we have a current session and uploaded files
  if (!currentSessionId.value || uploadedFiles.value.length === 0) return;
  
  const session = rwsSessionStore.sessions?.find(s => s.id === currentSessionId.value);
  if (!session || (!session.title || session.title === 'Untitled RWS Session' || session.title === 'New RWS Session' || !session.title.trim())) {
    const newTitle = generateTitleFromFiles(uploadedFiles.value);
    
    if (newTitle && newTitle !== session?.title) {
      try {
        await api.update_rws_session_title({ 
          session_id: currentSessionId.value, 
          title: newTitle 
        });
        if (session) {
          session.title = newTitle;
          // Update the session's lastMessageAt timestamp
          session.lastMessageAt = Date.now();
          // Re-sort sessions by last activity
          rwsSessionStore.sessions?.sort((a, b) => (b.lastMessageAt || 0) - (a.lastMessageAt || 0));
        }
      } catch (error) {
        console.error('Failed to update RWS session title after file change:', error);
        // Continue operation even if title update fails
      }
    }
  }
}

// Graph management functions
async function loadPaperGraph() {
  try {
    if (!currentSessionId.value) return;
    const graph = await api.get_paper_graph(currentSessionId.value);
    paperGraph.value = graph;
    updateGraphVisualization();
  } catch (error) {
    console.error('Failed to load paper graph:', error);
  }
}

async function updateGraphNodes() {
  try {
    if (!currentSessionId.value) return;
    await api.update_graph_nodes(uploadedFiles.value, currentSessionId.value);
    await loadPaperGraph();
  } catch (error) {
    console.error('Failed to update graph nodes:', error);
  }
}

function updateGraphVisualization() {
  if (!graphContainer.value) return;
  
  const containerRect = graphContainer.value.getBoundingClientRect();
  graphWidth.value = Math.max(600, containerRect.width);
  graphHeight.value = Math.max(400, uploadedFiles.value.length > 6 ? 500 : 400);  // More space for better visualization
  
  const numFiles = uploadedFiles.value.length;
  
  if (numFiles === 0) {
    paperConnections.value = [];
    return;
  }
  
  if (numFiles === 1) {
    // Single node at center
    uploadedFiles.value[0].x = graphWidth.value / 2;
    uploadedFiles.value[0].y = graphHeight.value / 2;
  } else if (numFiles === 2) {
    // Two nodes with more spacing
    uploadedFiles.value[0].x = graphWidth.value * 0.25;
    uploadedFiles.value[0].y = graphHeight.value / 2;
    uploadedFiles.value[1].x = graphWidth.value * 0.75;
    uploadedFiles.value[1].y = graphHeight.value / 2;
  } else {
    // Use force-directed layout for better node positioning and edge crossing reduction
    applyForceDirectedLayout();
  }
  
  // Update connections with proper edge calculations
  const connections = [];
  for (const edge of paperGraph.value.edges) {
    const fromFile = uploadedFiles.value.find(f => f.paper_id === edge.from);
    const toFile = uploadedFiles.value.find(f => f.paper_id === edge.to);
    
    if (fromFile && toFile) {
      // Calculate edge points to connect circle edges, not centers
      const dx = toFile.x - fromFile.x;
      const dy = toFile.y - fromFile.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      const nodeRadius = 20;
      
      // Calculate start and end points on circle edges
      const startX = fromFile.x + (dx / distance) * nodeRadius;
      const startY = fromFile.y + (dy / distance) * nodeRadius;
      const endX = toFile.x - (dx / distance) * nodeRadius;
      const endY = toFile.y - (dy / distance) * nodeRadius;
      
      // Create curved path with adaptive curvature to reduce edge crossings
      const midX = (startX + endX) / 2;
      const midY = (startY + endY) / 2;
      
      // Calculate adaptive curvature based on edge density and angle
      const edgeAngle = Math.atan2(dy, dx);
      const edgeLength = distance;
      
      // Base curvature that increases with shorter edges
      let curvature = Math.min(0.4, 0.1 + (200 / edgeLength));
      
      // Add variation based on edge index to spread out parallel edges
      const edgeIndex = paperGraph.value.edges.findIndex(e => 
        (e.from === edge.from && e.to === edge.to) || 
        (e.from === edge.to && e.to === edge.from)
      );
      const curvatureVariation = (edgeIndex % 3 - 1) * 0.15;
      curvature += curvatureVariation;
      
      const perpX = -(endY - startY) * curvature;
      const perpY = (endX - startX) * curvature;
      const controlX = midX + perpX;
      const controlY = midY + perpY;
      
      const path = `M ${startX} ${startY} Q ${controlX} ${controlY} ${endX} ${endY}`;
      
      connections.push({
        from: edge.from,
        to: edge.to,
        path: path,
        labelX: controlX,
        labelY: controlY - 10,
        relationship_type: edge.relationship_type,
        description: edge.description
      });
    }
  }
  paperConnections.value = connections;
}

// Force-directed layout algorithm for better node positioning
function applyForceDirectedLayout() {
  const nodes = uploadedFiles.value;
  const edges = paperGraph.value.edges;
  
  // Initialize positions if not set
  nodes.forEach((node, index) => {
    if (!node.x || !node.y) {
      // Start with circular initial positions with some randomization to avoid overlaps
      const angle = (2 * Math.PI * index) / nodes.length + (Math.random() - 0.5) * 0.5;
      const radius = Math.min(graphWidth.value, graphHeight.value) * (0.15 + Math.random() * 0.1);
      const centerX = graphWidth.value / 2 + (Math.random() - 0.5) * 50;
      const centerY = graphHeight.value / 2 + (Math.random() - 0.5) * 50;
      node.x = centerX + radius * Math.cos(angle);
      node.y = centerY + radius * Math.sin(angle);
    }
    // Initialize velocity
    node.vx = node.vx || 0;
    node.vy = node.vy || 0;
  });
  
  // Force simulation parameters
  const iterations = 300;
  const repulsionStrength = 12000;
  const attractionStrength = 0.01;
  const dampening = 0.9;
  const minDistance = 180; // Minimum distance between nodes
  const centerForce = 0.02;
  
  for (let iteration = 0; iteration < iterations; iteration++) {
    // Reset forces
    nodes.forEach(node => {
      node.fx = 0;
      node.fy = 0;
    });
    
    // Repulsion forces between all nodes
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const nodeA = nodes[i];
        const nodeB = nodes[j];
        
        const dx = nodeB.x - nodeA.x;
        const dy = nodeB.y - nodeA.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance > 0) {
          // Strong repulsion when nodes are too close
          const force = repulsionStrength / (distance * distance);
          const fx = (dx / distance) * force;
          const fy = (dy / distance) * force;
          
          nodeA.fx -= fx;
          nodeA.fy -= fy;
          nodeB.fx += fx;
          nodeB.fy += fy;
          
          // Additional force if nodes are too close
          if (distance < minDistance) {
            const extraForce = (minDistance - distance) * 0.5;
            const extraFx = (dx / distance) * extraForce;
            const extraFy = (dy / distance) * extraForce;
            
            nodeA.fx -= extraFx;
            nodeA.fy -= extraFy;
            nodeB.fx += extraFx;
            nodeB.fy += extraFy;
          }
        }
      }
    }
    
    // Attraction forces along edges
    edges.forEach(edge => {
      const nodeA = nodes.find(n => n.paper_id === edge.from);
      const nodeB = nodes.find(n => n.paper_id === edge.to);
      
      if (nodeA && nodeB) {
        const dx = nodeB.x - nodeA.x;
        const dy = nodeB.y - nodeA.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance > 0) {
          const force = attractionStrength * distance;
          const fx = (dx / distance) * force;
          const fy = (dy / distance) * force;
          
          nodeA.fx += fx;
          nodeA.fy += fy;
          nodeB.fx -= fx;
          nodeB.fy -= fy;
        }
      }
    });
    
    // Center force to keep nodes in the middle
    nodes.forEach(node => {
      const centerX = graphWidth.value / 2;
      const centerY = graphHeight.value / 2;
      node.fx += (centerX - node.x) * centerForce;
      node.fy += (centerY - node.y) * centerForce;
    });
    
    // Update velocities and positions
    nodes.forEach(node => {
      node.vx = (node.vx + node.fx) * dampening;
      node.vy = (node.vy + node.fy) * dampening;
      
      node.x += node.vx;
      node.y += node.vy;
      
      // Keep nodes within bounds with padding
      const padding = 60;
      node.x = Math.max(padding, Math.min(graphWidth.value - padding, node.x));
      node.y = Math.max(padding, Math.min(graphHeight.value - padding, node.y));
    });
  }
  
  // Clean up velocity properties
  nodes.forEach(node => {
    delete node.vx;
    delete node.vy;
    delete node.fx;
    delete node.fy;
  });
}

// Function to regenerate layout with slight randomization
function regenerateLayout() {
  // Clear current positions to force recalculation
  uploadedFiles.value.forEach(node => {
    delete node.x;
    delete node.y;
  });
  
  // Apply the force-directed layout again
  updateGraphVisualization();
}

function startAddingEdge() {
  isAddingEdge.value = true;
  selectedFromPaper.value = null;
}

// Target paper functions
function startChoosingTarget() {
  isChoosingTarget.value = true;
}

function cancelChoosingTarget() {
  isChoosingTarget.value = false;
}

async function selectTargetPaper(paperId) {
  if (!isChoosingTarget.value) return;
  
  try {
    // Set the target paper locally
    targetPaper.value = paperId;
    isChoosingTarget.value = false;
    
    // Update target paper in the backend if we have a session
    if (currentSessionId.value) {
      await api.set_target_paper(currentSessionId.value, paperId);
    }
    
    // Save to session state
    saveSessionState();
  } catch (error) {
    console.error('Failed to set target paper:', error);
    // Reset on error
    targetPaper.value = null;
    isChoosingTarget.value = false;
  }
}

async function clearTargetPaper() {
  try {
    // Clear the target paper locally
    targetPaper.value = null;
    
    // Clear target paper in the backend if we have a session
    if (currentSessionId.value) {
      await api.clear_target_paper(currentSessionId.value);
    }
    
    // Save to session state
    saveSessionState();
  } catch (error) {
    console.error('Failed to clear target paper:', error);
  }
}

function selectPaper(paperId) {
  if (isChoosingTarget.value) {
    selectTargetPaper(paperId);
  } else if (isAddingEdge.value) {
    selectPaperForEdge(paperId);
  }
}

function selectPaperForEdge(paperId) {
  if (!isAddingEdge.value) return;
  
  if (!selectedFromPaper.value) {
    selectedFromPaper.value = paperId;
  } else if (selectedFromPaper.value !== paperId) {
    // Open edge edit dialog
    currentEdge.value = {
      from: selectedFromPaper.value,
      to: paperId,
      relationship_type: 'relates_to',
      description: ''
    };
    edgeEditDialog.value = true;
  }
}

function cancelAddingEdge() {
  isAddingEdge.value = false;
  selectedFromPaper.value = null;
}

// Helper functions for node styling
function getNodeFill(paperId) {
  if (targetPaper.value === paperId) {
    return 'url(#targetGradient)';
  } else if (selectedFromPaper.value === paperId) {
    return 'url(#selectedGradient)';
  } else {
    return 'url(#nodeGradient)';
  }
}

function getNodeGlow(paperId) {
  if (targetPaper.value === paperId) {
    return 'url(#targetGlow)';
  } else if (selectedFromPaper.value === paperId) {
    return 'url(#selectedGlow)';
  } else {
    return 'url(#nodeGlow)';
  }
}

function getShortFilename(paperId) {
  const file = uploadedFiles.value.find(f => f.paper_id === paperId);
  if (!file) return 'Unknown';
  const filename = file.filename || 'Unknown';
  // Return first 15 characters with ... if longer
  return filename.length > 15 ? filename.substring(0, 15) + '...' : filename;
}

async function saveEdge() {
  try {
    if (!currentSessionId.value) return;
    await api.add_graph_edge({ 
      ...currentEdge.value, 
      session_id: currentSessionId.value 
    });
    await loadPaperGraph();
    edgeEditDialog.value = false;
    isAddingEdge.value = false;
    selectedFromPaper.value = null;
  } catch (error) {
    console.error('Failed to add edge:', error);
  }
}

async function removeEdge(fromPaper, toPaper) {
  try {
    if (!currentSessionId.value) return;
    await api.remove_graph_edge({ 
      from: fromPaper, 
      to: toPaper, 
      session_id: currentSessionId.value 
    });
    await loadPaperGraph();
  } catch (error) {
    console.error('Failed to remove edge:', error);
  }
}

async function completeGraphWithLLM() {
  if (!currentSessionId.value || uploadedFiles.value.length < 2 || isCompletingGraph.value) {
    return false;
  }
  
  isCompletingGraph.value = true;
  
  try {
    const result = await api.complete_graph(currentSessionId.value);
    
    if (result.success) {
      // Reload the graph to show new relationships
      await loadPaperGraph();
      return true;
    } else {
      console.error('Failed to complete graph:', result.error);
      return false;
    }
  } catch (error) {
    console.error('Error completing graph:', error);
    return false;
  } finally {
    isCompletingGraph.value = false;
  }
}

function getArrowPath(x1, y1, x2, y2) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const angle = Math.atan2(dy, dx);
  const length = Math.sqrt(dx * dx + dy * dy);
  
  // Shorten the line to not overlap with node circles
  const startX = x1 + 30 * Math.cos(angle);
  const startY = y1 + 30 * Math.sin(angle);
  const endX = x2 - 30 * Math.cos(angle);
  const endY = y2 - 30 * Math.sin(angle);
  
  // Arrow head
  const arrowLength = 10;
  const arrowAngle = Math.PI / 6;
  
  const arrowX1 = endX - arrowLength * Math.cos(angle - arrowAngle);
  const arrowY1 = endY - arrowLength * Math.sin(angle - arrowAngle);
  const arrowX2 = endX - arrowLength * Math.cos(angle + arrowAngle);
  const arrowY2 = endY - arrowLength * Math.sin(angle + arrowAngle);
  
  return {
    line: `M ${startX} ${startY} L ${endX} ${endY}`,
    arrow: `M ${endX} ${endY} L ${arrowX1} ${arrowY1} M ${endX} ${endY} L ${arrowX2} ${arrowY2}`
  };
}

// Generation function
async function generateRelatedWork() {
  if (uploadedFiles.value.length === 0 || isGenerating.value) return;
  
  // Create session if none exists
  if (!currentSessionId.value) {
    // Create session with guidance-based title if available
    const title = extractTitleFromInput(guidanceInputText.value || 'Related Work Generation');
    const newSession = await rwsSessionStore.createSession({ title });
    currentSessionId.value = newSession.id;
    localStorage.setItem('currentRwsSessionId', newSession.id);
  }
  
  // Save current guidance before we clear it (in case generation fails)
  const currentGuidance = guidanceInputText.value.trim();
  
  // Auto-update session title if it's empty and we have guidance or files
  const session = rwsSessionStore.sessions?.find(s => s.id === currentSessionId.value);
  if (session && (!session.title || session.title === 'Untitled RWS Session' || !session.title.trim())) {
    let newTitle = '';
    if (currentGuidance) {
      // Use guidance text for title generation
      newTitle = extractTitleFromInput(currentGuidance);
    } else if (uploadedFiles.value.length > 0) {
      // Generate title based on uploaded files
      newTitle = generateTitleFromFiles(uploadedFiles.value);
    }
    
    if (newTitle && newTitle !== session.title) {
      try {
        await api.update_rws_session_title({ 
          session_id: currentSessionId.value, 
          title: newTitle 
        });
        session.title = newTitle;
        // Update the session's lastMessageAt timestamp
        session.lastMessageAt = Date.now();
        // Re-sort sessions by last activity
        rwsSessionStore.sessions?.sort((a, b) => (b.lastMessageAt || 0) - (a.lastMessageAt || 0));
      } catch (error) {
        console.error('Failed to update RWS session title:', error);
        // Continue with generation even if title update fails
      }
    }
  }
  
  isGenerating.value = true;
  
  try {
    // Automatically complete the graph first if we have multiple papers
    if (uploadedFiles.value.length >= 2) {
      console.log('Auto-completing graph before generation...');
      await completeGraphWithLLM();
    }
    
    // Add user message with guidance if provided
    if (currentGuidance) {
      const userMessage = {
        id: Date.now().toString(),
        role: 'user',
        content: currentGuidance,
        created_at: new Date().toISOString()
      };
      rwsMessages.value.push(userMessage);
    }
    
    // Add empty assistant message for streaming
    const assistantMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString()
    };
    rwsMessages.value.push(assistantMessage);
    currentGeneratingMessageId.value = assistantMessage.id;
    
    // Extract guidance from input text
    const guidance = currentGuidance || null;
    
    // Clear the guidance input immediately after extraction to prevent it from being saved again
    guidanceInputText.value = '';
    
    // Let the backend handle all prompt generation - frontend only passes guidance
    const response = await api.stream_rws({
      session_id: currentSessionId.value,
      guidance: guidance
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
              assistantMessage.content += jsonData.content;
            }
          } catch (e) {
            remainingLines.push(line);
          }
        }
        
        accumulatedData = remainingLines.join('\n');
        
        if (accumulatedData) {
          assistantMessage.content += accumulatedData;
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
    if (assistantMessage) {
      assistantMessage.content = "Failed to generate related work. Please try again.";
    }
    // If generation failed, restore the guidance text so user can try again
    if (currentGuidance) {
      guidanceInputText.value = currentGuidance;
    }
  } finally {
    isGenerating.value = false;
    currentGeneratingMessageId.value = null;
    // Note: guidance input is either cleared (on success) or restored (on error)
    // No need to save session state here
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

async function copyLastAssistantMessage() {
  try {
    const lastAssistantMessage = rwsMessages.value
      .filter(m => m.role === 'assistant')
      .pop();
    
    if (lastAssistantMessage && lastAssistantMessage.content) {
      await navigator.clipboard.writeText(lastAssistantMessage.content);
      console.log('Content copied to clipboard');
    }
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
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
    
    initialLoading.value = true;
    
    // Initialize RWS sessions
    await rwsSessionStore.fetchAllSessions();
    const savedSessionId = localStorage.getItem('currentRwsSessionId');
    if (savedSessionId && rwsSessionStore.sessions.some(s => s.id === savedSessionId)) {
      currentSessionId.value = savedSessionId;
      await loadRwsSession(savedSessionId);
    } else {
      currentSessionId.value = null;
      // Clear all data when no session is selected - sessions should start clean
      uploadedFiles.value = [];
      paperConnections.value = [];
      paperGraph.value = { nodes: [], edges: [] };
      messages.value = [];
      generatedContent.value = '';
      guidanceInputText.value = '';
      rwsMessages.value = [];
    }
    
    initialLoading.value = false;
    
    // Wait for DOM to be fully rendered, then setup graph
    await nextTick();
    
    // Setup resize observer for graph container
    if (graphContainer.value) {
      resizeObserver = new ResizeObserver(() => {
        updateGraphVisualization();
      });
      resizeObserver.observe(graphContainer.value);
    }
    
    // Ensure graph visualization is updated after component is mounted
    updateGraphVisualization();
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
    // Ensure we have a current session
    if (!currentSessionId.value) {
      const newSession = await rwsSessionStore.createSession({ title: 'New RWS Session' });
      currentSessionId.value = newSession.id;
      localStorage.setItem('currentRwsSessionId', newSession.id);
    }
    
    // Update progress during upload
    progressItem.progress = 20;
    
    // Actually upload the file to backend
    const response = await api.upload_rws_file(currentSessionId.value, file);
    
    progressItem.progress = 80;
    
    if (response.success && response.file_info) {
      const fileInfo = response.file_info;
      
      // Add to uploaded files with position for graph
      const uploadedFile = {
        paper_id: fileInfo.paper_id,
        filename: fileInfo.filename,
        file_size: fileInfo.file_size,
        upload_date: new Date(fileInfo.upload_date * 1000).toISOString(),
        content_type: fileInfo.content_type,
        x: 50 + (uploadedFiles.value.length % 3) * 120,
        y: 50 + Math.floor(uploadedFiles.value.length / 3) * 80,
        selected: fileInfo.selected
      };
      
      uploadedFiles.value.push(uploadedFile);
      
      // Auto-update session title if it's still default after adding file
      await updateSessionTitleAfterFileChange();
      
      await updateGraphNodes();
      
      // Update graph visualization after adding file
      nextTick(() => {
        updateGraphVisualization();
      });
      
      progressItem.progress = 100;
      
      // Remove from progress after success
      setTimeout(() => {
        uploadProgress.value = uploadProgress.value.filter(p => p.id !== progressId);
      }, 2000);
      
    } else {
      throw new Error('Upload failed - no file info returned');
    }
    
  } catch (error) {
    console.error('Upload error:', error);
    progressItem.error = error.message || 'Upload failed';
    
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

// File selection dialog functions
async function openFileSelectionDialog() {
  // Ensure we have a current session - create one if needed
  if (!currentSessionId.value) {
    try {
      const newSession = await rwsSessionStore.createSession({ title: 'New RWS Session' });
      currentSessionId.value = newSession.id;
      localStorage.setItem('currentRwsSessionId', newSession.id);
    } catch (error) {
      console.error('Failed to create new session:', error);
      alert('Failed to create session. Please try again.');
      return;
    }
  }
  
  fileSelectionDialog.value = true;
  selectedGlobalFiles.value = [];
  await loadGlobalFiles();
}

async function loadGlobalFiles() {
  loadingGlobalFiles.value = true;
  try {
    const files = await api.get_user_files();
    globalFileList.value = files || [];
  } catch (error) {
    console.error('Failed to load global files:', error);
    globalFileList.value = [];
  } finally {
    loadingGlobalFiles.value = false;
  }
}

function isFileAlreadyAdded(paperId) {
  return uploadedFiles.value.some(file => file.paper_id === paperId);
}

function toggleSelectAll(event) {
  const checked = event.target.checked;
  if (checked) {
    // Select all files that aren't already added
    selectedGlobalFiles.value = globalFileList.value
      .filter(file => !isFileAlreadyAdded(file.paper_id))
      .map(file => file.paper_id);
  } else {
    selectedGlobalFiles.value = [];
  }
}

async function addSelectedFiles() {
  if (selectedGlobalFiles.value.length === 0 || !currentSessionId.value) {
    return;
  }
  
  try {
    const response = await api.add_files_to_rws_session(currentSessionId.value, selectedGlobalFiles.value);
    
    if (response.success) {
      // Reload session files to get the updated list
      const sessionFiles = await api.get_rws_session_files(currentSessionId.value);
      uploadedFiles.value = sessionFiles.map((file, index) => ({
        ...file,
        x: 50 + (index % 3) * 120,
        y: 50 + Math.floor(index / 3) * 80
      }));
      
      // Auto-update session title if it's still default after adding files
      await updateSessionTitleAfterFileChange();
      
      // Update graph nodes and visualization
      await updateGraphNodes();
      await nextTick();
      updateGraphVisualization();
      
      // Close dialog
      fileSelectionDialog.value = false;
      selectedGlobalFiles.value = [];
      
      console.log(`Successfully added ${response.added_count} files to session`);
    }
  } catch (error) {
    console.error('Failed to add files to session:', error);
    alert('Failed to add files to session. Please try again.');
  }
}

function formatDate(timestamp) {
  if (!timestamp) return 'Unknown';
  const date = new Date(timestamp * 1000); // Convert from seconds to milliseconds
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}


</script>

<style scoped>
.review-page {
  width: 100%;
  /* height: calc(100vh - 120px); */ /* Remove fixed height calculation */
  position: relative;
  display: flex;
  flex-direction: column;
  background-color: var(--surface-2);
  overflow: hidden;
}

.loading {
  text-align: center;
  padding: 2rem;
  background-color: var(--surface);
  border-radius: 8px;
  box-shadow: var(--shadow-1);
  margin-bottom: 2rem;
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

.two-panel-layout {
  display: flex;
  flex: 1;
  height: 100%;
  gap: 1rem;
  transition: all 0.3s ease;
}

.two-panel-layout.sidebar-collapsed {
  /* When sidebar is collapsed, we have more space */
  padding-left: 0.5rem;
}

/* Left Panel Styles */
.left-panel {
  flex: 0 0 50%;
  background: var(--surface);
  border-radius: 12px;
  box-shadow: var(--shadow-1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: flex-basis 0.3s ease;
}

.two-panel-layout.sidebar-collapsed .left-panel {
  flex: 0 0 50%;
}

.panel-header {
  padding: 1rem;
  border-bottom: 1px solid var(--border);
  background: var(--accent);
  color: white;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.file-upload-section {
  padding: 0.75rem;
}

.upload-buttons-container {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.upload-button {
  flex: 1;
  border: 2px dashed var(--border);
  border-radius: 8px;
  padding: 1rem 0.75rem;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
  background: var(--surface-2);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.upload-button:hover {
  border-color: var(--accent);
  background-color: #f3f4ff;
}

.upload-button.drag-over {
  border-color: var(--accent);
  background-color: #f3f4ff;
}

.upload-own-files {
  border-color: #2196f3;
}

.upload-own-files:hover {
  border-color: #1976d2;
  background-color: var(--accent-soft);
}

.add-from-list {
  border-color: #4caf50;
}

.add-from-list:hover {
  border-color: var(--success);
  background-color: #e8f5e8;
}

.upload-icon {
  font-size: 1.2rem;
  margin-bottom: 0.25rem;
}

.upload-text {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text);
}



.graph-section {
  flex: 1;
  padding: 0.75rem;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.graph-header h4 {
  margin: 0;
  color: var(--text);
  font-size: 1.1rem;
}

.graph-controls {
  display: flex;
  gap: 0.5rem;
}

.add-edge-btn {
  background: #4caf50;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
}

.add-edge-btn:hover {
  background: #45a049;
}

.cancel-edge-btn {
  background: var(--danger);
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
}

.cancel-edge-btn:hover {
  background: #da190b;
}

.regenerate-btn {
  background: #2196f3;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.regenerate-btn:hover {
  background: #1976d2;
  transform: translateY(-1px);
}

/* Target paper button styles */
.choose-target-btn {
  background: #e91e63;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.choose-target-btn:hover {
  background: #c2185b;
  transform: translateY(-1px);
}

.choose-target-btn.has-target {
  background: #ad1457;
  box-shadow: 0 2px 8px rgba(173,20,87,0.3);
}

.choose-target-btn.has-target:hover {
  background: #880e4f;
}

.cancel-target-btn {
  background: var(--danger);
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.3s ease;
}

.cancel-target-btn:hover {
  background: #da190b;
  transform: translateY(-1px);
}

.clear-target-btn {
  background: #ff5722;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.clear-target-btn:hover {
  background: #e64a19;
  transform: translateY(-1px);
}



.graph-container {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  overflow: auto;
  display: flex;
  flex-direction: column;
}

.graph-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-3);
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
  background: linear-gradient(135deg, var(--surface-2) 0%, #ffffff 100%);
  border-radius: 12px;
  border: 1px solid var(--border);
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
}

.paper-node {
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Enhanced node styling */
.paper-node {
  transition: all 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
  cursor: pointer;
}

.paper-node:hover .node-glow {
  opacity: 0.6 !important;
  transform: scale(1.1);
}

.paper-node:hover .node-main {
  stroke-width: 4;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.15));
  transform: scale(1.05);
}

.paper-node:hover .node-highlight {
  stroke-width: 2;
  stroke: rgba(255,255,255,0.7);
}

.paper-node:hover .number-bg {
  fill: rgba(255,255,255,1);
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
}

.paper-node .node-glow {
  transition: all 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.paper-node .node-main {
  transition: all 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
  filter: drop-shadow(0 2px 6px rgba(0,0,0,0.1));
}

.paper-node .node-highlight {
  transition: all 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.paper-node .number-bg {
  transition: all 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.05));
}

.paper-node .node-number {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  transition: all 0.3s ease;
}

.paper-node.adding-edge {
  cursor: crosshair;
}

.paper-node.adding-edge .node-main {
  stroke: #42a5f5;
  stroke-width: 4;
  stroke-dasharray: 8,4;
  animation: dash 2s linear infinite;
}

.paper-node.adding-edge .node-glow {
  opacity: 0.8 !important;
  animation: pulse 2s ease-in-out infinite;
}

.paper-node.selected .node-main {
  stroke: #ff9800;
  stroke-width: 5;
  filter: drop-shadow(0 4px 12px rgba(255,152,0,0.4));
  animation: selectedPulse 2s ease-in-out infinite;
}

.paper-node.selected .node-glow {
  opacity: 0.7 !important;
  transform: scale(1.15);
}

/* Target paper node styling */
.paper-node.choosing-target {
  cursor: crosshair;
}

.paper-node.choosing-target .node-main {
  stroke: #e91e63;
  stroke-width: 4;
  stroke-dasharray: 8,4;
  animation: dash 2s linear infinite;
}

.paper-node.choosing-target .node-glow {
  opacity: 0.8 !important;
  animation: pulse 2s ease-in-out infinite;
}

.paper-node.target-paper .node-main {
  stroke: #e91e63;
  stroke-width: 5;
  filter: drop-shadow(0 4px 12px rgba(233,30,99,0.4));
  animation: targetPulse 2s ease-in-out infinite;
}

.paper-node.target-paper .node-glow {
  opacity: 0.7 !important;
  transform: scale(1.15);
}

@keyframes targetPulse {
  0%, 100% {
    filter: drop-shadow(0 4px 12px rgba(233,30,99,0.4));
  }
  50% {
    filter: drop-shadow(0 6px 16px rgba(233,30,99,0.6));
  }
}

@keyframes dash {
  to {
    stroke-dashoffset: -12;
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.8;
  }
}

@keyframes selectedPulse {
  0%, 100% {
    filter: drop-shadow(0 4px 12px rgba(255,152,0,0.4));
  }
  50% {
    filter: drop-shadow(0 6px 16px rgba(255,152,0,0.6));
  }
}

/* Enhanced edge styling */
.connections g {
  transition: all 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.connections g:hover .edge-glow {
  opacity: 0.5 !important;
  stroke-width: 8 !important;
}

.connections g:hover .edge-main {
  stroke-width: 4 !important;
  opacity: 1 !important;
  filter: drop-shadow(0 2px 8px rgba(76,175,80,0.3));
}

.connections g:hover .edge-label-bg {
  stroke-width: 2;
  fill: rgba(255,255,255,1);
  filter: drop-shadow(0 2px 8px rgba(0,0,0,0.1));
  transform: scale(1.05);
}

.connections g:hover .edge-label {
  font-weight: 700;
  transform: scale(1.05);
}

.edge-glow {
  transition: all 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.edge-main {
  transition: all 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
  filter: drop-shadow(0 1px 3px rgba(0,0,0,0.1));
}

.edge-label-bg {
  transition: all 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
  filter: drop-shadow(0 1px 3px rgba(0,0,0,0.08));
}

.edge-label {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  transition: all 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.remove-edge-btn {
  transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.15));
  opacity: 0.8;
}

.remove-edge-btn:hover {
  opacity: 1;
  filter: drop-shadow(0 4px 12px rgba(244,67,54,0.5));
  stroke: rgba(255,255,255,0.9);
  stroke-width: 1;
}

.paper-list {
  flex: 1;
  padding: 0.75rem;
  overflow-y: auto;
}

.paper-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  background: var(--surface-2);
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
  background: var(--danger);
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
  flex: 0 0 50%;
  background: var(--surface);
  border-radius: 12px;
  box-shadow: var(--shadow-1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: flex-basis 0.3s ease;
}

.two-panel-layout.sidebar-collapsed .right-panel {
  flex: 0 0 50%;
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
  padding: 0.75rem 0.75rem 0.25rem 0.75rem;
}

.result-header h4 {
  margin: 0;
  color: var(--text);
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
  padding: 0 0.75rem 0.75rem 0.75rem;
  overflow-y: auto;
  border: 1px solid var(--border);
  margin: 0 0.75rem;
  border-radius: 8px;
  background: var(--surface-2);
}

.result-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-3);
  font-style: italic;
}

.generating-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1rem;
  color: var(--text-2);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid var(--accent);
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
  background: var(--surface);
  border-radius: 6px;
  margin: 1rem 0;
}

.rws-messages {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.rws-message {
  max-width: 85%;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  position: relative;
  line-height: 1.5;
  display: flex;
  align-items: flex-start;
  margin-bottom: 0.5rem;
}

.rws-message.user-message {
  align-self: flex-end;
  background-color: var(--accent-soft);
  color: #0d47a1;
  border-bottom-right-radius: 2px;
}

.rws-message.assistant-message {
  align-self: flex-start;
  background-color: var(--surface);
  color: var(--text);
  border-bottom-left-radius: 2px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.rws-message .message-content {
  overflow-wrap: break-word;
  word-wrap: break-word;
  word-break: break-word;
  font-size: 0.95rem;
}

.rws-message .message-content p {
  margin: 0 0 0.75rem;
}

.rws-message .message-content p:last-child {
  margin-bottom: 0;
}

.rws-message.generating {
  opacity: 0.8;
}

.rws-message.generating::after {
  content: '';
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--accent);
  animation: pulse 1.5s infinite;
  margin-left: 0.5rem;
}

.input-section {
  padding: 0.75rem;
  border-top: 1px solid var(--border);
  background: var(--surface-2);
}

.input-container {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.guidance-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.9rem;
  resize: vertical;
  min-height: 44px;
}

.guidance-input:focus {
  outline: none;
  border-color: var(--accent);
}



.generate-btn {
  width: 100%;
  background: var(--accent);
  color: white;
  border: none;
  padding: 0.75rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.generate-btn:disabled {
  background: var(--border);
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
  border-top: 1px solid var(--border);
  background: var(--surface-2);
}

.upload-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: var(--surface);
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
  color: var(--text-2);
}

.progress-bar {
  flex: 1;
  height: 10px;
  background: var(--surface-2);
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
  background: var(--danger);
}

.upload-status {
  font-size: 0.8rem;
  color: var(--text-2);
}

.error-text {
  color: var(--danger);
}

.success-text {
  color: #4caf50;
}

.progress-text {
  color: var(--text-2);
}

.supported-formats {
  font-size: 0.8rem;
  color: var(--text-3);
  margin-top: 0.5rem;
  padding: 0.3rem 0.6rem;
  background: #f0f8ff;
  border-radius: 4px;
  border: 1px solid var(--accent-soft);
}

/* Dialog Styles */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog-content {
  background: var(--surface);
  border-radius: 8px;
  padding: 1.5rem;
  min-width: 400px;
  max-width: 500px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.dialog-content h3 {
  margin: 0 0 1rem 0;
  color: var(--text);
}

.dialog-field {
  margin-bottom: 1rem;
}

.dialog-field label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: var(--text);
}

.dialog-field span {
  display: block;
  padding: 0.5rem;
  background: var(--surface-2);
  border-radius: 4px;
  color: var(--text-2);
  font-size: 0.9rem;
}

.dialog-field select,
.dialog-field textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-family: inherit;
  font-size: 0.9rem;
  box-sizing: border-box;
}

.dialog-field select:focus,
.dialog-field textarea:focus {
  outline: none;
  border-color: var(--accent);
}

.dialog-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.dialog-actions .cancel-btn {
  background: var(--text-2);
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.dialog-actions .save-btn {
  background: #4caf50;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.dialog-actions .cancel-btn:hover {
  background: var(--text-2);
}

.dialog-actions .save-btn:hover {
  background: #45a049;
}

/* File Selection Dialog Styles */
.file-selection-dialog {
  min-width: 600px;
  max-width: 700px;
  max-height: 80vh;
  overflow-y: auto;
}

.loading-files {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  gap: 1rem;
  color: var(--text-2);
}

.no-files {
  text-align: center;
  padding: 2rem;
  color: var(--text-2);
}

.no-files .hint {
  font-size: 0.9rem;
  color: var(--text-3);
  margin-top: 0.5rem;
}

.file-list {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 6px;
}

.file-list-header {
  padding: 1rem;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  font-weight: 600;
}

.file-list-header label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.file-items {
  max-height: 300px;
  overflow-y: auto;
}

.file-item {
  border-bottom: 1px solid var(--surface-2);
  transition: background-color 0.2s ease;
}

.file-item:hover {
  background-color: var(--surface-2);
}

.file-item.already-added {
  background-color: var(--surface-2);
  opacity: 0.6;
}

.file-item.already-added:hover {
  background-color: #e8e8e8;
}

.file-item-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  cursor: pointer;
  width: 100%;
}

.file-item.already-added .file-item-label {
  cursor: not-allowed;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-weight: 500;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 0.25rem;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  font-size: 0.875rem;
  color: var(--text-2);
}

.file-date {
  color: var(--text-3);
}

.already-added-label {
  color: #f57c00;
  font-weight: 500;
  font-size: 0.8rem;
}

.dialog-actions .save-btn:disabled {
  background: var(--border);
  cursor: not-allowed;
  opacity: 0.6;
}

.dialog-actions .save-btn:disabled:hover {
  background: var(--border);
  transform: none;
  box-shadow: none;
}


</style>

<style>
body {
  --app-max-width: none !important;
  /* overflow-x: hidden; */ /* Remove as we now control via JavaScript */
}
</style>