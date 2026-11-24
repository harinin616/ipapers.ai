<template>
  <div class="scrollable-paper-list" :style="{ height }">
    <span class="list-title">{{ displayTitle }}</span>
    <button class="close-btn" @click.stop="$emit('remove')" title="Remove list">
       <svg class="close-icon" viewBox="0 0 24 24">
         <path d="M18 6L6 18" />
         <path d="M6 6L18 18" />
       </svg>
    </button>
    <div class="scroll-body">
      <div v-if="isLoading" class="loading">Loading papers...</div>
      <div v-else-if="papers.length === 0" class="no-papers">No papers found</div>
      <div v-else class="papers-list">
        <PaperCard v-for="paper in papers" :key="paper.paper_id" :paper="paper" />
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent } from 'vue'
import PaperCard from './PaperCard.vue'

export default defineComponent({
  name: 'ScrollablePaperList',
  components: {
    PaperCard
  },
  emits: ['remove'],
  props: {
    papers: {
      type: Array,
      default: () => []
    },
    isLoading: {
      type: Boolean,
      default: false
    },
    title: {
      type: String,
      default: ''
    },
    height: {
      type: String,
      default: '450px'
    }
  },
  computed: {
    displayTitle() {
      return this.title && this.title.trim() !== '' ? this.title : 'Recent Papers';
    }
  }
})
</script>

<style scoped>
.scrollable-paper-list {
  position: relative;
  background-color: var(--surface);
  border-radius: 8px;
  box-shadow: var(--shadow-1);
  padding: 1rem;
  padding-top: 2.5rem; /* leave space for fixed title badge */
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-title {
  position: absolute;
  top: 8px;
  left: 12px;
  background-color: var(--accent-soft); /* lighter indigo */
  color: var(--accent); /* primary blue text */
  font-size: 0.8rem;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 4px;
  pointer-events: none;
}

.scroll-body {
  overflow-y: auto;
  flex-grow: 1;
}

.papers-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

.loading,
.no-papers {
  text-align: center;
  color: var(--text-2);
  padding: 2rem 0;
}

.close-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background-color: rgba(0,0,0,0.05);
}

.close-icon {
  width: 18px;
  height: 18px;
  stroke: var(--text-3); /* gray-400 */
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}
</style> 