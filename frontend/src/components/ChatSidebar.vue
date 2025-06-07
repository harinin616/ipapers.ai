<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h3>History</h3>
      <button @click="handleCreateSession" class="new-session-button">
        <svg class="icon-svg" viewBox="0 0 24 24" width="16" height="16">
          <path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z" />
        </svg>
        Add
      </button>
    </div>
    <ul class="session-list">
      <li
        v-for="session in chatSessions"
        :key="session.id"
        :class="['session-item', { active: session.id === currentSessionId }]"
        @click="handleSwitchSession(session.id)"
      >
        <span @click="handleSwitchSession(session.id)" class="session-title">
          {{ session.title || 'Untitled Session' }}
        </span>
        <button
          class="delete-btn"
          @click.stop="handleDeleteSession(session.id)"
          title="Delete session"
        >
          <svg class="icon-svg" viewBox="0 0 24 24" width="14" height="14">
            <path d="M9,3V4H4V6H5V19A2,2 0 0,0 7,21H17A2,2 0 0,0 19,19V6H20V4H15V3H9M7,6H17V19H7V6M9,8V17H11V8H9M13,8V17H15V8H13Z" />
          </svg>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

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

// Event handlers
const handleCreateSession = () => {
  emit('create-session')
}

const handleSwitchSession = (sessionId) => {
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
  background-color: #ffffff;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #e0e0e0;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #333;
}

.new-session-button {
  background-color: #3f51b5;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.new-session-button:hover {
  background-color: #303f9f;
}

.new-session-button .icon-svg {
  fill: currentColor;
  flex-shrink: 0;
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
  border-bottom: 1px solid #f0f0f0;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.session-item:hover {
  background-color: #f5f5f5;
}

.session-item.active {
  background-color: #e3f2fd;
  color: #0d47a1;
  font-weight: bold;
}

.session-title {
  display: block;
  max-width: 160px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.delete-btn {
  background: transparent;
  border: none;
  color: #666;
  font-size: 1rem;
  cursor: pointer;
  margin-left: 12px;
  padding: 4px;
  line-height: 1;
  border-radius: 4px;
  background-color: #fafafa;
  border: 1px solid #ddd;
  transition: background-color 0.2s, border-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.delete-btn .icon-svg {
  fill: currentColor;
}

.delete-btn:hover {
  color: #d32f2f;
  background-color: #ffecec;
  border-color: #f5c2c2;
}
</style> 