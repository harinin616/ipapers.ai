<template>
  <div class="daily-feed-page">
    <h1>Daily Feed</h1>
    <p class="subtitle">Explore trending papers across different disciplines</p>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Loading daily feed...</p>
    </div>

    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="loadDailyFeed" class="retry-btn">Retry</button>
    </div>

    <div v-else class="feed-content">
      <div class="categories-grid">
        <div 
          v-for="category in dailyFeedData.categories" 
          :key="category.category"
          class="category-card"
        >
          <h2 class="category-title">{{ category.display_name }}</h2>
          
          <!-- Word Cloud Section -->
          <div class="word-cloud-section">
            <div v-if="category.word_cloud_url" class="word-cloud-container">
              <img 
                :src="category.word_cloud_url" 
                :alt="`Word cloud for ${category.display_name}`"
                class="word-cloud-image"
                @error="handleImageError"
              />
            </div>
            <div v-else class="no-word-cloud">
              <div class="placeholder-cloud">
                <svg viewBox="0 0 24 24" class="cloud-icon">
                  <path d="M19.35 10.04A7.49 7.49 0 0 0 12 4C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 0 0 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z"/>
                </svg>
                <p>Word cloud coming soon</p>
              </div>
            </div>
          </div>

          <!-- Summaries Section -->
          <div class="summaries-section">
            <h3 class="summaries-title">Recent Trends</h3>
            <div v-if="category.summaries && category.summaries.length > 0" class="summaries-list">
              <div 
                v-for="(summary, index) in category.summaries" 
                :key="index"
                class="summary-accordion-item"
              >
                <div 
                  class="summary-header"
                  @click="toggleSummary(category.category, index)"
                  :class="{ 'expanded': isSummaryExpanded(category.category, index) }"
                >
                  <h4 class="summary-title">{{ extractSummaryTitle(summary) }}</h4>
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
                  <div class="summary-content" v-html="renderMarkdown(summary)"></div>
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

// Reactive data
const loading = ref(true)
const error = ref<string | null>(null)
const dailyFeedData = ref<{
  categories: Array<{
    category: string
    display_name: string
    word_cloud_url?: string
    summaries: string[]
  }>
  last_updated?: string
}>({
  categories: []
})

// Track expanded summaries: { categoryId: { summaryIndex: boolean } }
const expandedSummaries = ref<Record<string, Record<number, boolean>>>({})

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
  
  // Basic markdown parsing
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
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

// Extract title from markdown content
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
  margin-bottom: 2rem;
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

.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
}

.category-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.category-card:hover {
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

.word-cloud-section {
  margin-bottom: 1.5rem;
}

.word-cloud-container {
  text-align: center;
  margin-bottom: 1rem;
}

.word-cloud-image {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.no-word-cloud {
  text-align: center;
  padding: 2rem 0;
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
  .categories-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
  
  .daily-feed-page h1 {
    font-size: 2rem;
  }
  
  .category-card {
    padding: 1rem;
  }
}
</style> 