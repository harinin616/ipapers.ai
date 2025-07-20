<template>
  <div :class="['paper-card', { expanded }]">
    <h3 class="paper-title">
      <a :href="`https://arxiv.org/abs/${paper.paper_id}`" target="_blank" rel="noopener">
        {{ paper.title }}
      </a>
    </h3>
    
    <div class="paper-meta">
      <span class="paper-authors">{{ authorText }}</span>
      <span class="paper-date">{{ formattedDate }}</span>
    </div>
    
    <div class="paper-platform" v-if="paper.platform">
      <span class="platform-tag">{{ paper.platform.toUpperCase() }}</span>
    </div>
    
    <div class="paper-categories">
      <span 
        v-for="category in paper.categories" 
        :key="category" 
        class="category-tag"
      >
        {{ category }}
      </span>
    </div>
    
    <div class="abstract-wrapper">
      <p :class="['paper-abstract', { expanded }]">{{ expanded ? paper.abstract : truncatedAbstract }}</p>
      <div class="toggle-btn" @click.stop="toggleExpand">
        <svg v-if="!expanded" class="arrow-icon" viewBox="0 0 24 24">
          <polyline points="6 9 12 15 18 9" />
        </svg>
        <svg v-else class="arrow-icon" viewBox="0 0 24 24">
          <polyline points="6 15 12 9 18 15" />
        </svg>
      </div>
    </div>
    
    <div class="paper-actions">
      <a :href="paper.pdf_url" target="_blank" rel="noopener" class="action-button" @click="handlePdfClick">
        PDF
      </a>
      <button @click="goToPaperDetail" class="action-button">
        Details
      </button>
      <ChatButton :paper-id="paper.paper_id" />
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { paperStore } from '../stores/paperStore'
import type { Paper } from '../types/paper'
import ChatButton from './ChatButton.vue'
import api from '../services/api'

export default defineComponent({
  name: 'PaperCard',
  
  components: {
    ChatButton
  },
  
  props: {
    paper: {
      type: Object as () => Paper,
      required: true
    }
  },
  
  setup(props) {
    const router = useRouter();
    
    const expanded = ref(false);
    const toggleExpand = () => {
      expanded.value = !expanded.value;
    };
    
    // Format the authors list (show first 3 names, then "et al" if more)
    const authorText = computed(() => {
      const authors = props.paper.authors;
      if (!authors || authors.length === 0) return 'Unknown authors';
      
      if (authors.length <= 3) {
        return authors.join(', ');
      } else {
        return `${authors.slice(0, 3).join(', ')} et al.`;
      }
    });
    
    // Format the date
    const formattedDate = computed(() => {
      try {
        const date = new Date(props.paper.published_date);
        return date.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric'
        });
      } catch (e) {
        return props.paper.published_date;
      }
    });
    
    // Truncate abstract to reasonable length
    const truncatedAbstract = computed(() => {
      const abstract = props.paper.abstract;
      if (abstract.length <= 250) return abstract;
      
      return abstract.substring(0, 250) + '...';
    });
    
    // Handle PDF click with tracking
    const handlePdfClick = async () => {
      try {
        await api.click_paper(props.paper.paper_id);
      } catch (error) {
        console.error('Failed to record PDF click:', error);
      }
    };
    
    const goToPaperDetail = async () => {
      try {
        await api.click_paper(props.paper.paper_id);
        
        paperStore.setCurrentPaper(props.paper);
        router.push({ name: 'paper-detail' });
      } catch (error) {
        console.error('Failed to record details click:', error);
        paperStore.setCurrentPaper(props.paper);
        router.push({ name: 'paper-detail' });
      }
    };
    
    return {
      authorText,
      formattedDate,
      truncatedAbstract,
      expanded,
      toggleExpand,
      handlePdfClick,
      goToPaperDetail
    };
  }
})
</script>

<style scoped>
.paper-card {
  background-color: white;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 0.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.3s ease;
  display: flex;
  flex-direction: column;
  height: calc(100% - 0.5rem); /* Subtract bottom margin */
  overflow: hidden; /* Prevent content overflow */
  width: 100%; /* Ensure width doesn't exceed container */
  max-width: 100%; /* Ensure max width doesn't exceed container */
  box-sizing: border-box; /* Ensure padding doesn't increase element total width */
}

.paper-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.paper-title {
  margin-top: 0;
  margin-bottom: 0.75rem;
  font-size: 1.25rem;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  height: 2.8em; /* Approximately two lines height */
  width: 100%; /* Ensure width doesn't exceed container */
}

.paper-title a {
  color: #3f51b5;
  text-decoration: none;
  display: inline-block;
  max-width: 100%; /* Ensure links don't exceed container */
  overflow: hidden;
  text-overflow: ellipsis;
}

.paper-title a:hover {
  text-decoration: underline;
}

.paper-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
  color: #666;
}

.paper-authors {
  font-style: italic;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%;
}

.paper-platform {
  margin-bottom: 0.75rem;
  display: flex;
  justify-content: flex-start;
}

.platform-tag {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 0.3rem 0.8rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.paper-categories {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
  min-height: 1.8rem; /* Ensure categories area has minimum height */
}

.category-tag {
  background-color: #e3f2fd;
  color: #1976d2;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

.abstract-wrapper {
  position: relative;
  margin-bottom: 1rem;
}

.paper-abstract {
  color: #333;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex-grow: 1;
  height: 3.6em;
  position: relative;
}

.paper-abstract::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2em;
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0), #ffffff);
}

.paper-abstract.expanded {
  display: block;
  -webkit-line-clamp: unset;
  height: auto;
  overflow: visible;
}

.paper-abstract.expanded::after {
  display: none;
}

.toggle-btn {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 2px; /* slight offset */
  display: flex;
  justify-content: center;
  cursor: pointer;
}

.arrow-icon {
  width: 24px;
  height: 24px;
  stroke: #3f51b5;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}

.paper-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: auto; /* Push action buttons to the bottom */
}

.action-button {
  padding: 0.5rem 1rem;
  background-color: #f0f0f0;
  color: #333;
  border-radius: 4px;
  border: none;
  text-decoration: none;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.action-button:hover {
  background-color: #e0e0e0;
}

.chat-button {
  background-color: #3f51b5;
  color: white;
}

.chat-button:hover {
  background-color: #303f9f;
}
</style> 