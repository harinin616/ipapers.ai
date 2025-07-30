<template>
  <div class="simple-paper-card">
    <h3 class="paper-title">
      <a :href="`https://arxiv.org/abs/${paper.paper_id}`" target="_blank" rel="noopener">
        {{ paper.title }}
      </a>
    </h3>
    
    <div class="paper-action">
      <ChatButton :paper-id="paper.paper_id" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Paper } from '../types/paper'
import ChatButton from './ChatButton.vue'

defineProps<{
  paper: Paper
}>()
</script>

<style scoped>
.simple-paper-card {
  background-color: white;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 0.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.3s ease;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  min-height: 60px;
}

.simple-paper-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.paper-title {
  margin: 0;
  font-size: 1rem;
  line-height: 1.4;
  flex: 1;
  min-width: 0; /* Allow text to shrink */
}

.paper-title a {
  color: #3f51b5;
  text-decoration: none;
  display: block;
  white-space: normal;
  line-height: 1.4;
}

.paper-title a:hover {
  text-decoration: underline;
}

.paper-action {
  flex-shrink: 0; /* Prevent button from shrinking */
  margin-top: 0.25rem; /* Small top margin to align with first line of title */
}

/* Responsive design for mobile */
@media (max-width: 768px) {
  .simple-paper-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.75rem;
  }
  
  .paper-title {
    font-size: 0.95rem;
  }
  
  .paper-title a {
    white-space: normal;
    line-height: 1.3;
  }
}
</style> 