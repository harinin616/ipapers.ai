<template>
  <div class="sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-content">
      <!-- Header area with toggle and new session button -->
      <div class="sidebar-top">
        <!-- Toggle Button -->
        <button @click="toggleSidebar" class="hamburger-toggle" :title="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'">
          <svg class="icon-svg" viewBox="0 0 24 24" width="20" height="20">
            <path d="M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z" />
          </svg>
        </button>

        <!-- New Session Button -->
        <button @click="handleCreateSession" class="new-session-button" :class="{ 'collapsed': isCollapsed }" v-if="!isCollapsed">
          <svg class="icon-svg" viewBox="0 0 24 24" width="16" height="16">
            <path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z" />
          </svg>
          <span>New RWS</span>
        </button>

        <!-- New Session Button for collapsed state -->
        <button @click="handleCreateSession" class="new-session-button-collapsed" v-if="isCollapsed" title="New RWS session">
          <svg class="icon-svg" viewBox="0 0 24 24" width="20" height="20">
            <path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z" />
          </svg>
        </button>
      </div>

      <!-- Session List -->
      <ul class="session-list">
        <li
          v-for="session in rwsSessions"
          :key="session.id"
          :class="['session-item', { active: session.id === currentSessionId, collapsed: isCollapsed }]"
          @click="handleSwitchSession(session.id)"
          :title="isCollapsed ? (session.title || 'Untitled RWS Session') : ''"
        >
          <div class="session-icon" v-if="isCollapsed">
            <svg class="icon-svg" viewBox="0 0 24 24" width="16" height="16">
              <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
            </svg>
          </div>
          
          <!-- Session title - normal display or edit input -->
          <div v-show="!isCollapsed" class="session-title-container" @click.stop>
            <span 
              v-if="editingSessionId !== session.id" 
              @click="handleSwitchSession(session.id)" 
              class="session-title"
            >
              {{ session.title || 'Untitled RWS Session' }}
            </span>
            <input 
              v-else
              ref="editInput"
              v-model="editingTitle"
              @keydown.enter="saveTitle(session.id)"
              @keydown.esc="cancelEdit"
              @blur="saveTitle(session.id)"
              class="session-title-input"
              :placeholder="session.title || 'Untitled RWS Session'"
            />
          </div>

          <!-- Action buttons -->
          <div v-show="!isCollapsed" class="session-actions">
            <!-- Edit button -->
            <button
              v-if="editingSessionId !== session.id"
              class="edit-btn"
              @click.stop="startEdit(session.id, session.title)"
              title="Edit title"
            >
              <svg class="icon-svg" viewBox="0 0 24 24" width="14" height="14">
                <path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z" />
              </svg>
            </button>
            
            <!-- Save and Cancel buttons for editing -->
            <template v-if="editingSessionId === session.id">
              <button
                class="save-btn"
                @click.stop="saveTitle(session.id)"
                title="Save"
              >
                <svg class="icon-svg" viewBox="0 0 24 24" width="14" height="14">
                  <path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z" />
                </svg>
              </button>
              <button
                class="cancel-btn"
                @click.stop="cancelEdit"
                title="Cancel"
              >
                <svg class="icon-svg" viewBox="0 0 24 24" width="14" height="14">
                  <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z" />
                </svg>
              </button>
            </template>

            <!-- Delete button -->
            <button
              v-if="editingSessionId !== session.id"
              class="delete-btn"
              @click.stop="handleDeleteSession(session.id)"
              title="Delete session"
            >
              <svg class="icon-svg" viewBox="0 0 24 24" width="14" height="14">
                <path d="M9,3V4H4V6H5V19A2,2 0 0,0 7,21H17A2,2 0 0,0 19,19V6H20V4H15V3H9M7,6H17V19H7V6M9,8V17H11V8H9M13,8V17H15V8H13Z" />
              </svg>
            </button>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, ref, nextTick } from 'vue'
import api from '../services/api'

// Props
const props = defineProps({
  rwsSessions: {
    type: Array,
    default: () => []
  },
  currentSessionId: {
    type: [String, Number, null],
    default: null
  }
})

// Emits
const emit = defineEmits([
  'create-session',
  'switch-session', 
  'delete-session'
])

// Collapsed state
const isCollapsed = ref(false)

// Edit state
const editingSessionId = ref(null)
const editingTitle = ref('')
const editInput = ref(null)

// Toggle sidebar
const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

// Start editing title
const startEdit = async (sessionId, currentTitle) => {
  editingSessionId.value = sessionId
  editingTitle.value = currentTitle || ''
  await nextTick()
  if (editInput.value) {
    editInput.value.focus()
    editInput.value.select()
  }
}

// Save title
const saveTitle = async (sessionId) => {
  const newTitle = editingTitle.value.trim()
  const session = props.rwsSessions.find(s => s.id === sessionId)
  const originalTitle = session?.title || 'Untitled RWS Session'
  
  // If empty, keep original title
  const finalTitle = newTitle === '' ? originalTitle : newTitle
  
  // If no change, just cancel edit
  if (finalTitle === originalTitle) {
    cancelEdit()
    return
  }
  
  try {
    await api.update_rws_session_title({ 
      session_id: sessionId, 
      title: finalTitle 
    })
    
    // Update the session title in the local array
    if (session) {
      session.title = finalTitle
    }
    
    cancelEdit()
  } catch (error) {
    console.error('Failed to update RWS session title:', error)
    // You might want to show an error message to the user here
  }
}

// Cancel editing
const cancelEdit = () => {
  editingSessionId.value = null
  editingTitle.value = ''
}

// Handle create session
const handleCreateSession = () => {
  emit('create-session')
}

// Handle switch session
const handleSwitchSession = (sessionId) => {
  emit('switch-session', sessionId)
}

// Handle delete session
const handleDeleteSession = (sessionId) => {
  emit('delete-session', sessionId)
}
</script>

<style scoped>
.sidebar {
  width: 280px;
  background: #f8f9fa;
  border-right: 1px solid #e9ecef;
  display: flex;
  flex-direction: column;
  height: 100vh;
  transition: width 0.3s ease;
  position: relative;
}

.sidebar.collapsed {
  width: 60px;
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.sidebar-top {
  padding: 16px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hamburger-toggle {
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6c757d;
  transition: all 0.2s ease;
  align-self: flex-start;
}

.hamburger-toggle:hover {
  background: #e9ecef;
  color: #495057;
}

.new-session-button {
  background: #007bff;
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  width: 100%;
  justify-content: center;
}

.new-session-button:hover {
  background: #0056b3;
}

.new-session-button.collapsed {
  display: none;
}

.new-session-button-collapsed {
  background: #007bff;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  width: 100%;
}

.new-session-button-collapsed:hover {
  background: #0056b3;
}

.session-list {
  list-style: none;
  padding: 0;
  margin: 0;
  flex: 1;
  overflow-y: auto;
}

.session-item {
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f1f3f4;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s ease;
  position: relative;
}

.session-item:hover {
  background: #f1f3f4;
}

.session-item.active {
  background: #e3f2fd;
  border-left: 3px solid #007bff;
}

.session-item.collapsed {
  justify-content: center;
  padding: 12px 8px;
}

.session-icon {
  color: #6c757d;
  flex-shrink: 0;
}

.session-title-container {
  flex: 1;
  min-width: 0;
}

.session-title {
  display: block;
  font-size: 14px;
  color: #495057;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
}

.session-title-input {
  width: 100%;
  padding: 4px 8px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 14px;
  background: white;
}

.session-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.edit-btn,
.save-btn,
.cancel-btn,
.delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.edit-btn {
  color: #6c757d;
}

.edit-btn:hover {
  background: #e9ecef;
  color: #495057;
}

.save-btn {
  color: #28a745;
}

.save-btn:hover {
  background: #d4edda;
}

.cancel-btn {
  color: #6c757d;
}

.cancel-btn:hover {
  background: #e9ecef;
}

.delete-btn {
  color: #dc3545;
}

.delete-btn:hover {
  background: #f8d7da;
}

.icon-svg {
  fill: currentColor;
}

/* Scrollbar styling */
.session-list::-webkit-scrollbar {
  width: 6px;
}

.session-list::-webkit-scrollbar-track {
  background: transparent;
}

.session-list::-webkit-scrollbar-thumb {
  background: #ced4da;
  border-radius: 3px;
}

.session-list::-webkit-scrollbar-thumb:hover {
  background: #adb5bd;
}
</style> 