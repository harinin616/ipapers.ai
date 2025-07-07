<template>
  <div class="daily-feed-page">
    <h1>{{ getPageTitle() }}</h1>
    <p class="subtitle">Explore trending papers across different disciplines</p>
    
    <!-- Display Control -->
    <div class="display-controls">
      <label for="summaries-limit">Show summaries per category:</label>
      <select id="summaries-limit" v-model="maxSummaries" class="summaries-select">
        <option value="1">1 summary</option>
        <option value="2">2 summaries</option>
        <option value="3">3 summaries</option>
        <option value="4">4 summaries</option>
        <option value="5">5 summaries</option>
      </select>
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Loading daily feed...</p>
    </div>

    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="loadDailyFeed" class="retry-btn">Retry</button>
    </div>

    <div v-else class="daily-feed-content">
      <div v-for="category in dailyFeedData.categories" :key="category.category" class="category-section">
        <div class="category-content">
          <!-- Word Cloud Section -->
          <div class="wordcloud-section">
            <h2 class="category-title">{{ getCategoryTitle(category) }}</h2>
            <div v-if="category.word_cloud_url" class="wordcloud-container">
              <img 
                :src="category.word_cloud_url" 
                :alt="`${category.display_name} Word Cloud`"
                class="wordcloud-image"
                @error="handleImageError"
              />
            </div>
            <div v-else class="no-wordcloud">
              <p>Word cloud not available</p>
            </div>
          </div>

          <!-- Summaries Section -->
          <div class="summaries-section">
            <h3 class="summaries-title">Recent Trends</h3>
            <div v-if="category.summaries && category.summaries.length > 0" class="summaries-list">
              <div 
                v-for="(summary, index) in category.summaries.slice(0, maxSummaries)" 
                :key="index"
                class="summary-accordion-item"
              >
                <div 
                  class="summary-header"
                  @click="toggleSummary(category.category, index)"
                  :class="{ 'expanded': isSummaryExpanded(category.category, index) }"
                >
                  <h4 class="summary-title">{{ getSummaryTitle(summary) }}</h4>
                  <div class="toggle-icon">
                    <svg 
                      viewBox="0 0 24 24" 
                      :class="{ 'rotated': isSummaryExpanded(category.category, index) }"
                    >
                      <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
                    </svg>
                  </div>
                </div>
                <div 
                  class="summary-content-wrapper"
                  :class="{ 'expanded': isSummaryExpanded(category.category, index) }"
                >
                  <div class="summary-content" v-html="renderMarkdown(getSummaryContent(summary))"></div>
                </div>
              </div>
            </div>
            <div v-else class="no-summaries">
              <p>There is no new paper for today. Check back later for the latest trends!</p>
            </div>
          </div>
        </div>
      </div>

      <div v-if="dailyFeedData.last_updated" class="last-updated">
        <p>Last updated: {{ formatDate(dailyFeedData.last_updated) }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

// Enhanced type definitions for the new data structure
interface SummaryData {
  content: string
  title: string
  phrase?: string
  paper_count?: number
}

interface CategoryData {
  category: string
  display_name: string
  paper_count?: number
  word_cloud_url?: string
  summaries: SummaryData[]
}

interface DailyFeedData {
  date?: string
  total_papers?: number
  categories: CategoryData[]
  last_updated?: string
}

// Reactive data
const loading = ref(true)
const error = ref<string | null>(null)
const maxSummaries = ref(3) // 🎯 Control how many summaries to show per category
const dailyFeedData = ref<DailyFeedData>({
  categories: []
})

// Track expanded summaries: { categoryId: { summaryIndex: boolean } }
const expandedSummaries = ref<Record<string, Record<number, boolean>>>({})

// Get page title with date and total papers
const getPageTitle = (): string => {
  if (dailyFeedData.value.date && dailyFeedData.value.total_papers !== undefined) {
    return `${dailyFeedData.value.date} Daily Feed (${dailyFeedData.value.total_papers} papers)`
  }
  return 'Daily Feed'
}

// Get category title with paper count
const getCategoryTitle = (category: CategoryData): string => {
  if (category.paper_count !== undefined) {
    return `${category.display_name} (${category.paper_count} papers)`
  }
  return category.display_name
}

// Get summary title with paper count
const getSummaryTitle = (summary: SummaryData | string): string => {
  if (typeof summary === 'string') {
    // Legacy format - extract title from markdown
    return extractSummaryTitle(summary)
  }
  
  // New format with metadata
  if (summary.paper_count !== undefined) {
    return `${summary.title} (${summary.paper_count} papers)`
  }
  return summary.title
}

// Get summary content (handles both old and new formats)
const getSummaryContent = (summary: SummaryData | string): string => {
  if (typeof summary === 'string') {
    return summary
  }
  return summary.content
}

// Load daily feed data from static JSON file
const loadDailyFeed = async () => {
  loading.value = true
  error.value = null
  
  try {
    const response = await fetch('/daily_feed/daily_feed.json')
    if (!response.ok) {
      throw new Error(`Failed to load daily feed data: ${response.status}`)
    }
    const data = await response.json()
    dailyFeedData.value = data
  } catch (err) {
    console.error('Failed to load daily feed:', err)
    error.value = 'Failed to load daily feed. Please try again later.'
  } finally {
    loading.value = false
  }
}

// Handle image loading errors
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
  console.warn('Failed to load word cloud image:', img.src)
}

// Simple markdown rendering function
const renderMarkdown = (text: string): string => {
  if (!text) return ''
  
  // Enhanced markdown parsing with better feature support
  let html = text
    
  // Handle headers (# ## ###)
  html = html.replace(/^### (.*$)/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.*$)/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.*$)/gm, '<h1>$1</h1>')
  
  // Handle bold and italic text
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')
  
  // Handle code blocks and inline code
  html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
  html = html.replace(/`(.*?)`/g, '<code>$1</code>')
  
  // Handle links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
  
  // Handle unordered lists (- or *)
  html = html.replace(/^[\s]*[-\*]\s+(.*$)/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
  
  // Handle ordered lists (1. 2. etc.)
  html = html.replace(/^[\s]*\d+\.\s+(.*$)/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>)/gs, (match) => {
    // Only wrap with <ol> if it's not already wrapped with <ul>
    if (match.includes('<ul>')) {
      return match;
    }
    return '<ol>' + match + '</ol>';
  })
  
  // Handle blockquotes (> text)
  html = html.replace(/^>\s+(.*$)/gm, '<blockquote>$1</blockquote>')
  
  // Handle line breaks and paragraphs
  // Split by double newlines for paragraphs
  const paragraphs = html.split(/\n\s*\n/);
  html = paragraphs.map(paragraph => {
    // Don't wrap headers, lists, blockquotes, or code blocks in <p> tags
    if (paragraph.match(/^<(h[1-6]|ul|ol|blockquote|pre|div)/)) {
      return paragraph;
    }
    // Replace single newlines with <br> within paragraphs
    paragraph = paragraph.replace(/\n/g, '<br>');
    return paragraph.trim() ? `<p>${paragraph}</p>` : '';
  }).join('\n');
  
  return html
}

// Format date
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Extract title from markdown content (for backward compatibility)
const extractSummaryTitle = (markdownContent: string): string => {
  if (!markdownContent) return 'Summary'
  
  // Extract H1 title from markdown
  const h1Match = markdownContent.match(/^#\s+(.+)/m)
  if (h1Match) {
    // Clean up the title by removing extra text after colons
    let title = h1Match[1].trim()
    // Remove patterns like ": A Tsunami of Innovation..." or similar
    title = title.replace(/:\s*.+$/, '')
    return title
  }
  
  return 'Summary'
}

// Toggle summary expansion
const toggleSummary = (categoryId: string, summaryIndex: number) => {
  if (!expandedSummaries.value[categoryId]) {
    expandedSummaries.value[categoryId] = {}
  }
  expandedSummaries.value[categoryId][summaryIndex] = !expandedSummaries.value[categoryId][summaryIndex]
}

// Check if summary is expanded
const isSummaryExpanded = (categoryId: string, summaryIndex: number): boolean => {
  return expandedSummaries.value[categoryId]?.[summaryIndex] || false
}

// Load data on component mount
onMounted(() => {
  loadDailyFeed()
})
</script>

<style scoped>
.daily-feed-page {
  max-width: 1400px;
  margin: 2rem auto;
  padding: 0 1.5rem;
}

.daily-feed-page h1 {
  font-size: 2.5rem;
  font-weight: 700;
  text-align: center;
  color: #3f51b5;
  margin-bottom: 0.5rem;
}

.subtitle {
  text-align: center;
  font-size: 1.1rem;
  color: #666;
  margin-bottom: 1rem;
}

.display-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.display-controls label {
  font-weight: 600;
  color: #495057;
  font-size: 0.9rem;
}

.summaries-select {
  padding: 0.5rem 1rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background: white;
  font-size: 0.9rem;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.summaries-select:hover {
  border-color: #3f51b5;
}

.summaries-select:focus {
  outline: none;
  border-color: #3f51b5;
  box-shadow: 0 0 0 2px rgba(63, 81, 181, 0.2);
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3f51b5;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error {
  text-align: center;
  color: #d32f2f;
  padding: 2rem 0;
}

.retry-btn {
  background-color: #3f51b5;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 1rem;
  transition: background-color 0.2s;
}

.retry-btn:hover {
  background-color: #2c3e9e;
}

.daily-feed-content {
  margin-bottom: 2rem;
}

.category-section {
  margin-bottom: 3rem;
  max-width: 1200px;
  margin-left: auto;
  margin-right: auto;
}

.category-content {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.category-content:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.category-title {
  font-size: 1.3rem;
  font-weight: 600;
  color: #3f51b5;
  margin-bottom: 1rem;
  text-align: center;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 0.5rem;
}

.wordcloud-section {
  margin-bottom: 1.5rem;
}

.wordcloud-container {
  text-align: center;
  margin-bottom: 1rem;
}

.wordcloud-image {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.no-wordcloud {
  text-align: center;
  padding: 2rem 0;
  color: #6c757d;
}

.placeholder-cloud {
  color: #999;
}

.cloud-icon {
  width: 48px;
  height: 48px;
  fill: #ccc;
  margin-bottom: 0.5rem;
}

.summaries-section {
  border-top: 1px solid #e0e0e0;
  padding-top: 1rem;
}

.summaries-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 1rem;
}

.summaries-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.summary-accordion-item {
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  overflow: hidden;
  transition: box-shadow 0.2s ease;
}

.summary-accordion-item:hover {
  box-shadow: 0 2px 8px rgba(63, 81, 181, 0.1);
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  cursor: pointer;
  background: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
  transition: background-color 0.2s ease;
}

.summary-header:hover {
  background: #f0f0f0;
}

.summary-header.expanded {
  background: #e8eaf6;
  border-bottom-color: #3f51b5;
}

.summary-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  flex: 1;
}

.summary-header.expanded .summary-title {
  color: #3f51b5;
}

.toggle-icon {
  margin-left: 1rem;
  transition: transform 0.3s ease;
}

.toggle-icon svg {
  width: 24px;
  height: 24px;
  fill: #666;
  transition: transform 0.3s ease, fill 0.2s ease;
}

.toggle-icon svg.rotated {
  transform: rotate(180deg);
}

.summary-header.expanded .toggle-icon svg {
  fill: #3f51b5;
}

.summary-content-wrapper {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease-out, padding 0.3s ease-out;
}

.summary-content-wrapper.expanded {
  max-height: 2000px; /* Large enough to accommodate content */
  padding: 1rem;
}

.summary-content {
  line-height: 1.6;
  color: #333;
}

.summary-content strong {
  color: #3f51b5;
}

.summary-content code {
  background: #e3f2fd;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.summary-content pre {
  background: #f5f5f5;
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
  border-left: 4px solid #3f51b5;
  margin: 1rem 0;
}

.summary-content pre code {
  background: transparent;
  padding: 0;
  font-size: 0.85em;
  color: #333;
}

.summary-content a {
  color: #3f51b5;
  text-decoration: none;
  border-bottom: 1px solid #3f51b5;
  transition: all 0.2s ease;
}

.summary-content a:hover {
  color: #2c3e9e;
  border-bottom-color: #2c3e9e;
  background: rgba(63, 81, 181, 0.1);
}

.summary-content ul, .summary-content ol {
  margin: 1rem 0;
  padding-left: 1.5rem;
}

.summary-content li {
  margin-bottom: 0.5rem;
}

.summary-content blockquote {
  margin: 1rem 0;
  padding: 1rem;
  background: #f8f9fa;
  border-left: 4px solid #3f51b5;
  font-style: italic;
  color: #555;
}

.summary-content h2 {
  color: #3f51b5;
  font-size: 1.3rem;
  margin: 1.5rem 0 0.5rem 0;
  font-weight: 600;
}

.summary-content h3 {
  color: #333;
  font-size: 1.1rem;
  margin: 1rem 0 0.5rem 0;
  font-weight: 600;
}

.summary-content p {
  margin: 1rem 0;
}

/* Remove the h1 title from content since it's shown in the header */
.summary-content h1 {
  display: none;
}

.no-summaries {
  text-align: center;
  color: #666;
  font-style: italic;
  padding: 1rem 0;
  background: #f9f9f9;
  border-radius: 8px;
  border: 2px dashed #ddd;
}

.last-updated {
  text-align: center;
  margin-top: 2rem;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 8px;
  color: #666;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .category-section {
    margin-bottom: 2rem;
  }
  
  .daily-feed-page h1 {
    font-size: 1.8rem;
  }
  
  .category-content {
    padding: 1rem;
  }
  
  .display-controls {
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style> 