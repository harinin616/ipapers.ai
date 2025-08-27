<template>
  <div v-if="summary" class="search-summary">
    <div class="summary-header">
      <h3>📋 Search Summary</h3>
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
      
      <div v-else class="summary-full">
        <div v-for="(section, index) in formattedSummary" :key="index" class="summary-section">
          <h4 v-if="section.type === 'heading'" class="section-heading">{{ section.content }}</h4>
          <p v-else-if="section.type === 'paragraph'" class="section-paragraph" v-html="section.content"></p>
        </div>
      </div>
    </div>
    
    <div v-if="!isExpanded" class="summary-footer">
      <small class="summary-meta">
        AI-generated summary based on {{ paperCount }} papers
      </small>
    </div>
  </div>
</template>

<script>
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
    },
    
    formattedSummary() {
      if (!this.summary) return []
      
      const sections = []
      const lines = this.summary.split('\n')
      
      for (const line of lines) {
        const trimmedLine = line.trim()
        if (!trimmedLine) continue
        
        // Handle headings
        if (trimmedLine.startsWith('#')) {
          const headingText = trimmedLine.replace(/^#+\s*/, '')
          sections.push({
            type: 'heading',
            content: headingText
          })
        } else {
          // Handle regular paragraphs with link conversion
          const formattedContent = this.formatLinks(trimmedLine)
          sections.push({
            type: 'paragraph',
            content: formattedContent
          })
        }
      }
      
      return sections
    }
  },
  methods: {
    toggleExpanded() {
      this.isExpanded = !this.isExpanded
    },
    
    formatLinks(text) {
      // Convert markdown-style links [text](url) to HTML links
      return text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    }
  }
}
</script>

<style scoped>
.search-summary {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #eee;
  background: #f8f9fa;
}

.summary-header h3 {
  margin: 0;
  color: #333;
  font-size: 1.1rem;
  font-weight: 600;
}

.toggle-btn {
  background: #3f51b5;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background-color 0.2s;
}

.toggle-btn:hover {
  background: #303f9f;
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
  color: #666;
  line-height: 1.5;
  font-size: 0.95rem;
}

.fade-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2rem;
  background: linear-gradient(to bottom, transparent, white);
  pointer-events: none;
}

.summary-full {
  color: #333;
  line-height: 1.6;
}

.summary-section {
  margin-bottom: 1rem;
}

.section-heading {
  color: #333;
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
  padding-bottom: 0.3rem;
  border-bottom: 1px solid #eee;
}

.section-paragraph {
  margin: 0 0 0.8rem 0;
  color: #555;
  line-height: 1.6;
}

.section-paragraph a {
  color: #3f51b5;
  text-decoration: none;
}

.section-paragraph a:hover {
  text-decoration: underline;
}

.summary-footer {
  padding: 0.8rem 1.5rem;
  background: #f8f9fa;
  border-top: 1px solid #eee;
}

.summary-meta {
  color: #666;
  font-size: 0.85rem;
  font-style: italic;
}

.expanded {
  max-height: none !important;
}

@media (max-width: 768px) {
  .summary-header {
    flex-direction: column;
    gap: 0.8rem;
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
