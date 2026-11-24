<template>
  <article :class="['paper-card', { expanded }]">
    <div class="paper-top">
      <span v-if="paper.platform" class="chip chip-accent">{{ paper.platform.toUpperCase() }}</span>
      <time class="paper-date" :datetime="paper.published_date">{{ formattedDate }}</time>
    </div>

    <h3 class="paper-title">
      <a :href="paperUrl" target="_blank" rel="noopener">{{ paper.title }}</a>
    </h3>

    <p class="paper-authors">{{ authorText }}</p>

    <div v-if="paper.categories && paper.categories.length" class="paper-categories">
      <span v-for="category in paper.categories.slice(0, 4)" :key="category" class="chip">{{ category }}</span>
      <span v-if="paper.categories.length > 4" class="chip">+{{ paper.categories.length - 4 }}</span>
    </div>

    <p :class="['paper-abstract', { expanded }]">{{ expanded ? paper.abstract : truncatedAbstract }}</p>
    <button v-if="paper.abstract && paper.abstract.length > 250" type="button" class="toggle-btn" :aria-expanded="expanded" @click.stop="toggleExpand">
      {{ expanded ? 'Show less' : 'Show more' }}
    </button>

    <div class="paper-actions">
      <button @click="goToPaperDetail" class="btn btn-primary btn-sm">Details</button>
      <a :href="paper.pdf_url" target="_blank" rel="noopener" class="btn btn-sm" @click="handlePdfClick">PDF</a>
      <ChatButton :paper-id="paper.paper_id" :platform="paper.platform" />
    </div>
  </article>
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
    
    // Generate appropriate URL based on platform
    const paperUrl = computed(() => {
      const platform = props.paper.platform || 'arxiv';
      const paperId = props.paper.paper_id;
      
      if (platform === 'arxiv') {
        return `https://arxiv.org/abs/${paperId}`;
      } else if (['acl', 'emnlp', 'naacl', 'eacl', 'coling'].includes(platform)) {
        return `https://aclanthology.org/${paperId}`;
      } else {
        return props.paper.pdf_url;
      }
    });
    
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
        await api.click_paper(props.paper.paper_id, props.paper.platform);
      } catch (error) {
        console.error('Failed to record PDF click:', error);
      }
    };
    
    const goToPaperDetail = async () => {
      try {
        await api.click_paper(props.paper.paper_id, props.paper.platform);
        
        paperStore.setCurrentPaper(props.paper);
        router.push({ 
          name: 'paper-detail',
          params: {
            id: props.paper.paper_id,
            platform: props.paper.platform || 'arxiv'
          }
        });
      } catch (error) {
        console.error('Failed to record details click:', error);
        paperStore.setCurrentPaper(props.paper);
        router.push({ 
          name: 'paper-detail',
          params: {
            id: props.paper.paper_id,
            platform: props.paper.platform || 'arxiv'
          }
        });
      }
    };
    
    return {
      paperUrl,
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
  display: flex; flex-direction: column; gap: var(--sp-2);
  width: 100%; box-sizing: border-box;
  padding: var(--sp-5); margin-bottom: var(--sp-3);
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg);
  box-shadow: var(--shadow-1);
  transition: box-shadow .2s var(--ease), border-color .2s var(--ease), transform .2s var(--ease);
}
.paper-card:hover { box-shadow: var(--shadow-2); border-color: var(--border-strong); }
.paper-top { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-3); }
.paper-date { font-size: var(--fs-xs); color: var(--text-3); }
.paper-title {
  margin: var(--sp-1) 0 0; font-family: var(--font-serif); font-weight: 600;
  font-size: var(--fs-xl); line-height: 1.3; letter-spacing: -.005em;
}
.paper-title a { color: var(--text); text-decoration: none; }
.paper-title a:hover { color: var(--accent); }
.paper-authors { margin: 0; font-size: var(--fs-sm); color: var(--text-2); }
.paper-categories { display: flex; flex-wrap: wrap; gap: 6px; margin-top: var(--sp-1); }
.paper-abstract { margin: var(--sp-2) 0 0; font-size: var(--fs-sm); line-height: 1.65; color: var(--text-2); }
.toggle-btn {
  align-self: flex-start; padding: 0; background: none; border: none; cursor: pointer;
  font: 500 var(--fs-xs)/1 var(--font-sans); color: var(--accent);
}
.toggle-btn:hover { text-decoration: underline; }
.paper-actions { display: flex; align-items: center; flex-wrap: wrap; gap: var(--sp-2); margin-top: var(--sp-3); }
@media (max-width: 520px) { .paper-card { padding: var(--sp-4); } .paper-title { font-size: var(--fs-lg); } }
</style>