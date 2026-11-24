<template>
  <div class="sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-content">
      <!-- Header area with toggle and new chat button -->
      <div class="sidebar-top">
        <!-- Toggle Button -->
        <button @click="toggleSidebar" class="hamburger-toggle" :title="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'">
          <svg class="icon-svg" viewBox="0 0 24 24" width="20" height="20">
            <path d="M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z" />
          </svg>
        </button>

        <!-- New Chat Button -->
        <button @click="handleCreateSession" class="new-chat-button" :class="{ 'collapsed': isCollapsed }" v-if="!isCollapsed">
          <svg class="icon-svg" viewBox="0 0 24 24" width="16" height="16">
            <path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z" />
          </svg>
          <span>New chat</span>
        </button>

        <!-- New Chat Button for collapsed state -->
        <button @click="handleCreateSession" class="new-chat-button-collapsed" v-if="isCollapsed" title="New chat">
          <svg class="icon-svg" viewBox="0 0 24 24" width="20" height="20">
            <path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z" />
          </svg>
        </button>
      </div>

      <!-- Session List -->
      <ul class="session-list">
        <li
          v-for="session in chatSessions"
          :key="session.id"
          :class="['session-item', { active: session.id === currentSessionId, collapsed: isCollapsed }]"
          @click="handleSwitchSession(session.id)"
          :title="isCollapsed ? (session.title || 'Untitled Session') : ''"
        >
          <div class="session-icon" v-if="isCollapsed">
            <svg class="icon-svg" viewBox="0 0 24 24" width="16" height="16">
              <path d="M12,3C13.73,3 16.39,3.81 18.19,5.13C18.69,5.48 19,6.05 19,6.66C19,7.27 18.69,7.84 18.19,8.19C16.39,9.5 13.73,10.31 12,10.31C10.27,10.31 7.61,9.5 5.81,8.19C5.31,7.84 5,7.27 5,6.66C5,6.05 5.31,5.48 5.81,5.13C7.61,3.81 10.27,3 12,3M12,11.31C13.73,11.31 16.39,12.12 18.19,13.44C18.69,13.79 19,14.36 19,14.97C19,15.58 18.69,16.15 18.19,16.5C16.39,17.81 13.73,18.62 12,18.62C10.27,18.62 7.61,17.81 5.81,16.5C5.31,16.15 5,15.58 5,14.97C5,14.36 5.31,13.79 5.81,13.44C7.61,12.12 10.27,11.31 12,11.31Z" />
            </svg>
          </div>
          
          <!-- Session title - normal display or edit input -->
          <div v-show="!isCollapsed" class="session-title-container" @click.stop>
            <span 
              v-if="editingSessionId !== session.id" 
              @click="handleSwitchSession(session.id)" 
              class="session-title"
            >
              {{ session.title || 'Untitled Session' }}
            </span>
            <input 
              v-else
              ref="editInput"
              v-model="editingTitle"
              @keydown.enter="saveTitle(session.id)"
              @keydown.esc="cancelEdit"
              @blur="saveTitle(session.id)"
              class="session-title-input"
              :placeholder="session.title || 'Untitled Session'"
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
  chatSessions: {
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
const isCollapsed = ref(true)

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
  const session = props.chatSessions.find(s => s.id === sessionId)
  const originalTitle = session?.title || 'Untitled Session'
  
  // If empty, keep original title
  const finalTitle = newTitle === '' ? originalTitle : newTitle
  
  // If no change, just cancel edit
  if (finalTitle === originalTitle) {
    cancelEdit()
    return
  }
  
  try {
    await api.update_session_title({ 
      session_id: sessionId, 
      title: finalTitle 
    })
    
    // Update the session title in the local array
    if (session) {
      session.title = finalTitle
    }
    
    cancelEdit()
  } catch (error) {
    console.error('Failed to update session title:', error)
    // You might want to show an error message to the user here
  }
}

// Cancel editing
const cancelEdit = () => {
  editingSessionId.value = null
  editingTitle.value = ''
}

// Event handlers
const handleCreateSession = () => {
  emit('create-session')
}

const handleSwitchSession = (sessionId) => {
  if (editingSessionId.value === sessionId) return // Prevent switching while editing
  emit('switch-session', sessionId)
}

const handleDeleteSession = (sessionId) => {
  emit('delete-session', sessionId)
}
</script>

<style scoped>
.sidebar {
  width: 240px;
  min-width: 200px;
  max-width: 260px;
  background-color: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s ease;
  position: relative;
}

.sidebar.collapsed {
  width: 60px;
  min-width: 60px;
  max-width: 60px;
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.sidebar-top {
  display: flex;
  flex-direction: column;
  padding: 12px;
  gap: 12px;
  border-bottom: 1px solid var(--border);
}

.sidebar.collapsed .sidebar-top {
  align-items: center;
  padding: 12px 8px;
}

.hamburger-toggle {
  background-color: transparent;
  border: none;
  border-radius: 8px;
  width: 40px;
  height: 40px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  align-self: flex-start;
}

.hamburger-toggle:hover {
  background-color: var(--surface-2);
}

.hamburger-toggle .icon-svg {
  fill: #444;
  transition: fill 0.2s ease;
}

.new-chat-button {
  background-color: transparent;
  border: 1px solid var(--border);
  border-radius: 24px;
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 0.9rem;
  color: #444;
  transition: all 0.2s ease;
  width: 100%;
}

.new-chat-button:hover {
  background-color: var(--surface-2);
  border-color: #d0d0d0;
}

.new-chat-button .icon-svg {
  fill: currentColor;
  flex-shrink: 0;
}

.new-chat-button-collapsed {
  background-color: transparent;
  border: none;
  border-radius: 8px;
  width: 40px;
  height: 40px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.new-chat-button-collapsed:hover {
  background-color: var(--surface-2);
}

.new-chat-button-collapsed .icon-svg {
  fill: #444;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  margin: 0;
  padding: 0;
  list-style: none;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;  
  padding: 10px 12px;
  cursor: pointer;
  font-size: 0.95rem;
  color: #444;
  border-bottom: 1px solid var(--surface-2);
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
  transition: all 0.3s ease;
  border-radius: 8px;
  margin: 4px 8px;
}

.session-item.collapsed {
  justify-content: center;
  padding: 12px 8px;
  margin: 4px 8px;
}

.session-item:hover {
  background-color: var(--surface-2);
}

.session-item.active {
  background-color: #e8f0fe;
  color: #1a73e8;
  font-weight: 500;
}

.session-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-2);
}

.session-icon .icon-svg {
  fill: currentColor;
}

.session-item.active .session-icon .icon-svg {
  fill: #1a73e8;
}

.session-title-container {
  flex: 1;
  min-width: 0;
}

.session-title {
  display: block;
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  transition: opacity 0.3s ease;
  cursor: pointer;
}

.session-title-input {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 0.95rem;
  background-color: var(--surface);
  outline: none;
}

.session-title-input:focus {
  border-color: #1a73e8;
  box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
}

.session-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.edit-btn,
.save-btn,
.cancel-btn,
.delete-btn {
  background: transparent;
  border: none;
  color: var(--text-2);
  cursor: pointer;
  padding: 4px;
  line-height: 1;
  border-radius: 4px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.edit-btn .icon-svg,
.save-btn .icon-svg,
.cancel-btn .icon-svg,
.delete-btn .icon-svg {
  fill: currentColor;
}

.edit-btn:hover {
  color: #1a73e8;
  background-color: #e8f0fe;
}

.save-btn:hover {
  color: #4caf50;
  background-color: #e8f5e8;
}

.cancel-btn:hover {
  color: #ff9800;
  background-color: #fff3e0;
}

.delete-btn:hover {
  color: var(--danger);
  background-color: #ffecec;
}

/* Hide scrollbar for collapsed state */
.sidebar.collapsed .session-list {
  overflow-y: auto;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.sidebar.collapsed .session-list::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}
</style> 