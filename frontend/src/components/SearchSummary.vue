<template>
  <div v-if="summary" class="search-summary">
    <div class="summary-header">
      <h3>📋 Research Summary</h3>
      <div class="summary-controls">
        <button @click="toggleExpanded" class="toggle-btn">
          {{ isExpanded ? 'Collapse' : 'Expand' }}
        </button>
      </div>
    </div>
    
    <div class="summary-content" :class="{ expanded: isExpanded }">
      <div v-if="!isExpanded" class="summary-preview">
        <p>{{ previewText }}</p>
        <div class="fade-overlay"></div>
      </div>
      
      <div v-else class="summary-full" v-html="renderMarkdown(summary)"></div>
    </div>
    
    <div v-if="!isExpanded" class="summary-footer">
      <small class="summary-meta">
        AI-generated summary based on {{ paperCount }} papers
      </small>
    </div>
  </div>
</template>

<script>
import { marked } from 'marked'

export default {
  name: 'SearchSummary',
  props: {
    summary: {
      type: String,
      default: null
    },
    paperCount: {
      type: Number,
      default: 0
    }
  },
  data() {
    return {
      isExpanded: false
    }
  },
  computed: {
    previewText() {
      if (!this.summary) return ''
      
      // Extract the first paragraph after the title
      const lines = this.summary.split('\n').filter(line => line.trim())
      let firstParagraph = ''
      
      for (const line of lines) {
        if (!line.startsWith('#') && line.trim().length > 0) {
          firstParagraph = line.trim()
          break
        }
      }
      
      // Limit to approximately 150 characters
      if (firstParagraph.length > 150) {
        return firstParagraph.substring(0, 150) + '...'
      }
      
      return firstParagraph || this.summary.substring(0, 150) + '...'
    }
  },
  methods: {
    toggleExpanded() {
      this.isExpanded = !this.isExpanded
    },
    
    renderMarkdown(content) {
      if (!content) return ''
      
      // Configure marked options
      marked.setOptions({
        breaks: true,
        gfm: true
      })
      
      return marked(content)
    }
  }
}
</script>

<style scoped>
.search-summary {
  background: linear-gradient(135deg, #f8fffe 0%, #f1f8ff 100%);
  border: 1px solid #e1f5fe;
  border-radius: 12px;
  margin-bottom: 2rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 1.5rem 1rem 1.5rem;
  border-bottom: 1px solid #e1f5fe;
  background: rgba(255, 255, 255, 0.5);
}

.summary-header h3 {
  margin: 0;
  color: #1976d2;
  font-size: 1.2rem;
  font-weight: 600;
}

.toggle-btn {
  background: #1976d2;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.toggle-btn:hover {
  background: #1565c0;
  transform: translateY(-1px);
}

.summary-content {
  position: relative;
  padding: 1.5rem;
}

.summary-preview {
  position: relative;
  max-height: 4rem;
  overflow: hidden;
}

.summary-preview p {
  margin: 0;
  color: #333;
  line-height: 1.6;
  font-size: 1rem;
}

.fade-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2rem;
  background: linear-gradient(to bottom, transparent, #f8fffe);
  pointer-events: none;
}

.summary-full {
  color: #333;
  line-height: 1.7;
}

.summary-full :deep(h1) {
  color: #1976d2;
  font-size: 1.4rem;
  margin-bottom: 1rem;
  border-bottom: 2px solid #e1f5fe;
  padding-bottom: 0.5rem;
}

.summary-full :deep(h2) {
  color: #1976d2;
  font-size: 1.2rem;
  margin: 1.5rem 0 0.8rem 0;
}

.summary-full :deep(h3) {
  color: #424242;
  font-size: 1.1rem;
  margin: 1.2rem 0 0.6rem 0;
}

.summary-full :deep(p) {
  margin-bottom: 1rem;
  text-align: justify;
}

.summary-full :deep(a) {
  color: #1976d2;
  text-decoration: none;
  border-bottom: 1px dotted #1976d2;
  transition: all 0.3s ease;
}

.summary-full :deep(a:hover) {
  color: #1565c0;
  border-bottom-style: solid;
}

.summary-full :deep(strong) {
  color: #1976d2;
  font-weight: 600;
}

.summary-footer {
  padding: 0.8rem 1.5rem;
  background: rgba(255, 255, 255, 0.7);
  border-top: 1px solid #e1f5fe;
}

.summary-meta {
  color: #666;
  font-style: italic;
}

.expanded {
  max-height: none !important;
}

@media (max-width: 768px) {
  .summary-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }
  
  .summary-controls {
    align-self: flex-end;
  }
  
  .summary-content {
    padding: 1rem;
  }
  
  .summary-footer {
    padding: 0.8rem 1rem;
  }
}
</style>
