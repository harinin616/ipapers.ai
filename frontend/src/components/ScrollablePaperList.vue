<template>
  <div class="scrollable-paper-list" :style="{ height }">
    <span v-if="title" class="list-title">{{ title }}</span>
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
      default: 'Recent Papers'
    },
    height: {
      type: String,
      default: '450px'
    }
  }
})
</script>

<style scoped>
.scrollable-paper-list {
  position: relative;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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
  background-color: #e8eaf6; /* lighter indigo */
  color: #3f51b5; /* primary blue text */
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
  color: #666;
  padding: 2rem 0;
}
</style> 