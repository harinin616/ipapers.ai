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
        AI-generated summary based on the search results
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
.search-summary { margin-bottom: var(--sp-4); padding: var(--sp-4) var(--sp-5); background: var(--accent-soft); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: var(--r-lg); }
.summary-header { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-3); }
.summary-header h3 { margin: 0; font-size: var(--fs-md); }
.toggle-btn { height: 28px; padding: 0 var(--sp-3); font: 500 var(--fs-xs)/1 var(--font-sans); color: var(--accent); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-sm); cursor: pointer; }
.toggle-btn:hover { background: var(--surface-2); }
.summary-content { position: relative; margin-top: var(--sp-3); color: var(--text); font-size: var(--fs-sm); line-height: 1.7; }
.summary-preview { position: relative; max-height: 5.4em; overflow: hidden; }
.summary-preview p { margin: 0; }
.fade-overlay { position: absolute; inset: auto 0 0 0; height: 2.4em; background: linear-gradient(to bottom, transparent, var(--accent-soft)); pointer-events: none; }
.section-heading { margin: var(--sp-3) 0 var(--sp-1); font-size: var(--fs-sm); color: var(--text); }
.section-paragraph { margin: 0 0 var(--sp-2); }
.summary-footer { margin-top: var(--sp-2); }
.summary-meta { color: var(--text-3); }
</style>
