<template>
  <div class="daily-feed-page">
    <div class="header-section">
      <h1>{{ getPageTitle() }}</h1>
      <!-- Subscription Management Button - Under Title -->
      <router-link to="/subscription" class="subscription-manage-btn">
        <svg viewBox="0 0 24 24" fill="none" class="manage-icon">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" stroke="currentColor" stroke-width="2"/>
          <polyline points="22,6 12,13 2,6" stroke="currentColor" stroke-width="2"/>
        </svg>
        <span>Manage Subscription</span>
      </router-link>
    </div>
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

    <!-- Audio Global Controls -->
    <div class="audio-global-controls" v-if="currentAudioId">
      <!-- Play/Pause Button -->
      <button 
        @click="toggleGlobalPlayPause" 
        class="global-play-pause-btn"
        :title="isGlobalAudioPlaying() ? 'Pause' : 'Play'"
      >
        <svg v-if="isGlobalAudioPlaying()" viewBox="0 0 24 24" class="pause-icon">
          <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" fill="currentColor"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" class="play-icon">
          <path d="M8 5v14l11-7z" fill="currentColor"/>
        </svg>
      </button>
      
      <div class="audio-progress-section">
        <div class="audio-time-display">
          <span class="current-time">{{ formatTime(audioCurrentTime) }}</span>
        </div>
        <div 
          class="audio-progress-container"
          @click="seekAudio"
          title="Click to seek"
        >
          <div class="audio-progress-bar">
            <div 
              class="audio-progress-fill"
              :style="{ width: audioProgress + '%' }"
            ></div>
            <div 
              class="audio-progress-handle"
              :style="{ left: audioProgress + '%' }"
            ></div>
          </div>
        </div>
        <div class="audio-time-display">
          <span class="total-time">{{ formatTime(audioDuration) }}</span>
        </div>
      </div>
      
      <button 
        @click="stopAllPlayback" 
        class="global-close-btn"
        title="Close audio player"
      >
        <svg viewBox="0 0 24 24" class="close-icon">
          <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" fill="currentColor"/>
        </svg>
      </button>
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
      <div v-for="category in getAllCategories()" :key="category.category" class="category-section">
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
                  <div class="header-controls">
                    <!-- Audio Button -->
                    <button 
                      v-if="getAudioUrl(summary)"
                      @click.stop="toggleAudio(category.category, index, summary)"
                      class="audio-btn"
                      :class="{ 
                        'playing': isAudioPlaying(category.category, index),
                        'paused': isAudioPaused(category.category, index)
                      }"
                      :title="getAudioButtonTitle(category.category, index)"
                    >
                      <svg v-if="!isAudioPlaying(category.category, index) && !isAudioPaused(category.category, index)" viewBox="0 0 24 24" class="volume-icon">
                        <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" fill="currentColor"/>
                      </svg>
                      <svg v-else-if="isAudioPlaying(category.category, index)" viewBox="0 0 24 24" class="pause-icon">
                        <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" fill="currentColor"/>
                      </svg>
                      <svg v-else viewBox="0 0 24 24" class="volume-icon">
                        <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" fill="currentColor"/>
                      </svg>
                    </button>
                    <div class="toggle-icon">
                      <svg 
                        viewBox="0 0 24 24" 
                        :class="{ 'rotated': isSummaryExpanded(category.category, index) }"
                      >
                        <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
                      </svg>
                    </div>
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
              <p>There is no new paper for this category today.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

// Enhanced type definitions for the new data structure
interface SummaryData {
  content: string
  title: string
  phrase?: string
  paper_count?: number
  audio_url?: string
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

// Audio playback interfaces
interface AudioState {
  categoryId: string
  summaryIndex: number
  audio: HTMLAudioElement | null
  isPaused: boolean
  duration: number
  currentTime: number
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

// Audio playback state management
const currentAudioId = ref<string | null>(null)
const audioState = ref<AudioState | null>(null)
const audioVolume = ref(1.0)
const audioPlaybackRate = ref(1.0)

// Audio progress tracking
const audioProgress = ref(0) // 0-100 percentage
const audioDuration = ref(0) // in seconds
const audioCurrentTime = ref(0) // in seconds

// Audio playback methods
// Generate unique ID for audio tracking
const getAudioId = (categoryId: string, summaryIndex: number): string => {
  return `audio-${categoryId}-${summaryIndex}`
}

// Get audio URL for a summary
const getAudioUrl = (summary: SummaryData | string): string | null => {
  if (typeof summary === 'string') {
    return null // Legacy format doesn't have audio
  }
  return summary.audio_url || null
}

// Check if a specific summary audio is currently playing
const isAudioPlaying = (categoryId: string, summaryIndex: number): boolean => {
  const audioId = getAudioId(categoryId, summaryIndex)
  return currentAudioId.value === audioId && 
         !!audioState.value?.audio && 
         !audioState.value?.audio.paused &&
         !(audioState.value?.isPaused ?? false)
}

// Check if a specific summary audio is paused
const isAudioPaused = (categoryId: string, summaryIndex: number): boolean => {
  const audioId = getAudioId(categoryId, summaryIndex)
  return currentAudioId.value === audioId && 
         (audioState.value?.isPaused ?? false) === true
}

// Get audio button title for accessibility
const getAudioButtonTitle = (categoryId: string, summaryIndex: number): string => {
  if (isAudioPlaying(categoryId, summaryIndex)) return 'Pause audio'
  if (isAudioPaused(categoryId, summaryIndex)) return 'Resume audio'
  return 'Play audio narration'
}

// Start audio playback for a summary
const startAudio = (categoryId: string, summaryIndex: number, summary: SummaryData | string) => {
  const audioUrl = getAudioUrl(summary)
  if (!audioUrl) return
  
  // Stop any current audio
  stopAudio()
  
  const audio = new Audio(audioUrl)
  audio.volume = audioVolume.value
  audio.playbackRate = audioPlaybackRate.value
  
  // Set up event handlers
  audio.onloadstart = () => {
    currentAudioId.value = getAudioId(categoryId, summaryIndex)
    audioState.value = {
      categoryId,
      summaryIndex,
      audio,
      isPaused: false,
      duration: 0,
      currentTime: 0
    }
  }
  
  audio.onloadedmetadata = () => {
    if (audioState.value) {
      audioState.value.duration = audio.duration
      audioDuration.value = audio.duration
    }
  }
  
  audio.ontimeupdate = () => {
    if (audioState.value) {
      audioState.value.currentTime = audio.currentTime
      audioCurrentTime.value = audio.currentTime
      audioProgress.value = audioDuration.value > 0 ? (audio.currentTime / audioDuration.value) * 100 : 0
    }
  }
  
  audio.onplay = () => {
    if (audioState.value) {
      audioState.value.isPaused = false
    }
  }
  
  audio.onpause = () => {
    if (audioState.value) {
      audioState.value.isPaused = true
    }
  }
  
  audio.onended = () => {
    currentAudioId.value = null
    audioState.value = null
    audioProgress.value = 0
    audioDuration.value = 0
    audioCurrentTime.value = 0
  }
  
  audio.onerror = (event) => {
    console.error('Audio playback error:', event)
    currentAudioId.value = null
    audioState.value = null
    audioProgress.value = 0
    audioDuration.value = 0
    audioCurrentTime.value = 0
  }
  
  // Start playing
  audio.play().catch(error => {
    console.error('Failed to play audio:', error)
    currentAudioId.value = null
    audioState.value = null
    audioProgress.value = 0
    audioDuration.value = 0
    audioCurrentTime.value = 0
  })
}

// Pause current audio
const pauseAudio = () => {
  if (audioState.value?.audio && !audioState.value.audio.paused) {
    audioState.value.audio.pause()
    audioState.value.isPaused = true
  }
}

// Resume paused audio
const resumeAudio = () => {
  if (audioState.value?.audio && audioState.value.audio.paused) {
    audioState.value.audio.play().catch(error => {
      console.error('Failed to resume audio:', error)
    })
    audioState.value.isPaused = false
  }
}

// Stop all audio
const stopAudio = () => {
  if (audioState.value?.audio) {
    audioState.value.audio.pause()
    audioState.value.audio.currentTime = 0
  }
  currentAudioId.value = null
  audioState.value = null
  audioProgress.value = 0
  audioDuration.value = 0
  audioCurrentTime.value = 0
}

// Handle seeking in audio
const seekAudio = (event: MouseEvent) => {
  if (!audioState.value?.audio || audioDuration.value <= 0) return
  
  event.preventDefault()
  event.stopPropagation()
  
  try {
    const progressContainer = event.currentTarget as HTMLElement
    const rect = progressContainer.getBoundingClientRect()
    const clickX = event.clientX - rect.left
    const percentage = Math.max(0, Math.min(1, clickX / rect.width))
    const newTime = percentage * audioDuration.value
    
    console.log('Seeking to:', newTime, 'seconds (', percentage * 100, '%)')
    
    // Store current play state
    const wasPlaying = !audioState.value.audio.paused && !audioState.value.isPaused
    
    // Update audio time
    audioState.value.audio.currentTime = newTime
    audioCurrentTime.value = newTime
    audioProgress.value = percentage * 100
    
    // Maintain the play state
    if (wasPlaying && audioState.value.audio.paused) {
      // If it was playing, make sure it continues playing
      audioState.value.audio.play().catch(console.error)
      audioState.value.isPaused = false
    } else if (!wasPlaying) {
      // If it was paused, keep it paused
      audioState.value.isPaused = true
    }
  } catch (error) {
    console.error('Error seeking audio:', error)
  }
}

// Global play/pause toggle for current audio
const toggleGlobalPlayPause = () => {
  if (!audioState.value?.audio) return
  
  if (audioState.value.audio.paused || audioState.value.isPaused) {
    resumeAudio()
  } else {
    pauseAudio()
  }
}

// Check if any audio is currently playing (not paused)
const isGlobalAudioPlaying = (): boolean => {
  return !!audioState.value?.audio && 
         !audioState.value.audio.paused && 
         !audioState.value.isPaused
}

// Format time for display (MM:SS)
const formatTime = (seconds: number): string => {
  if (isNaN(seconds) || seconds < 0) return '0:00'
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.floor(seconds % 60)
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
}

// Toggle audio for a summary
const toggleAudio = (categoryId: string, summaryIndex: number, summary: SummaryData | string) => {
  const audioId = getAudioId(categoryId, summaryIndex)
  
  if (currentAudioId.value === audioId) {
    if (audioState.value?.isPaused || audioState.value?.audio?.paused) {
      resumeAudio()
    } else {
      pauseAudio()
    }
  } else {
    startAudio(categoryId, summaryIndex, summary)
  }
}

// Stop all playback (Audio only now)
const stopAllPlayback = () => {
  stopAudio()
}

// Get page title with date and total papers
const getPageTitle = (): string => {
  if (dailyFeedData.value.date && dailyFeedData.value.total_papers !== undefined) {
    const paperText = dailyFeedData.value.total_papers === 1 ? 'paper' : 'papers'
    return `${dailyFeedData.value.date} Daily Feed (${dailyFeedData.value.total_papers} ${paperText})`
  }
  return 'Daily Feed'
}

// Get category title with paper count
const getCategoryTitle = (category: CategoryData): string => {
  if (category.paper_count !== undefined) {
    const paperText = category.paper_count === 1 ? 'paper' : 'papers'
    return `${category.display_name} (${category.paper_count} ${paperText})`
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
    const paperText = summary.paper_count === 1 ? 'paper' : 'papers'
    return `${summary.title} (${summary.paper_count} ${paperText})`
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

// Define expected categories
const expectedCategories = [
  { key: 'computer_science_cs', name: 'Computer Science' },
  { key: 'economics_econ', name: 'Economics' },
  { key: 'electrical_engineering_&_systems_science_eess', name: 'Electrical Engineering & Systems Science' },
  { key: 'mathematics_math', name: 'Mathematics' },
  { key: 'physics', name: 'Physics' },
  { key: 'quantitative_biology_q-bio', name: 'Quantitative Biology' },
  { key: 'quantitative_finance_q-fin', name: 'Quantitative Finance' },
  { key: 'statistics_stat', name: 'Statistics' }
]

// Get all categories (actual + missing) with placeholder data for missing ones
const getAllCategories = (): CategoryData[] => {
  const actualCategories = dailyFeedData.value.categories || []
  const actualCategoryKeys = new Set(actualCategories.map(cat => cat.category))
  
  const allCategories: CategoryData[] = []
  
  // Add all expected categories
  for (const expectedCat of expectedCategories) {
    const actualCategory = actualCategories.find(cat => cat.category === expectedCat.key)
    
    if (actualCategory) {
      // Use actual category data but override display name to remove abbreviations
      allCategories.push({
        ...actualCategory,
        display_name: expectedCat.name
      })
    } else {
      // Create placeholder for missing category
      allCategories.push({
        category: expectedCat.key,
        display_name: expectedCat.name,
        paper_count: 0,
        word_cloud_url: undefined,
        summaries: []
      })
    }
  }
  
  return allCategories
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

// Component lifecycle
onMounted(() => {
  loadDailyFeed()
})

onUnmounted(() => {
  stopAudio()
})
</script>

<style scoped>
.daily-feed-page {
  max-width: 1400px;
  margin: 2rem auto;
  padding: 0 1.5rem;
}

.subscription-manage-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: #3f51b5;
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(63, 81, 181, 0.2);
  margin-top: 1rem;
}

.subscription-manage-btn:hover {
  background: #2c3e9e;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(63, 81, 181, 0.3);
}

.manage-icon {
  width: 18px;
  height: 18px;
}

.header-section {
  text-align: center;
  margin-bottom: 0.5rem;
}

.daily-feed-page h1 {
  font-size: 2.5rem;
  font-weight: 700;
  text-align: center;
  color: #3f51b5;
  margin: 0;
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
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
  max-width: 1400px;
  margin-left: auto;
  margin-right: auto;
}

.category-section {
  display: flex;
  flex-direction: column;
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

.header-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.audio-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  transition: opacity 0.2s ease;
}

.audio-btn:hover {
  opacity: 0.8;
}

.audio-btn.playing {
  opacity: 0.7;
}

.audio-btn.paused {
  opacity: 0.7;
}

.audio-btn .volume-icon,
.audio-btn .pause-icon {
  fill: #4caf50;
  width: 24px;
  height: 24px;
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

.audio-global-controls {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.95);
  padding: 10px 20px;
  border-radius: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  gap: 15px;
  z-index: 1000;
  backdrop-filter: blur(10px);
  min-width: 400px;
  max-width: 600px;
}

.global-play-pause-btn {
  background: #4caf50;
  color: white;
  border: none;
  padding: 10px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.2);
  width: 44px;
  height: 44px;
}

.global-play-pause-btn:hover {
  background: #45a049;
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.global-play-pause-btn .play-icon,
.global-play-pause-btn .pause-icon {
  width: 22px;
  height: 22px;
}

.global-close-btn {
  background: #f44336;
  color: white;
  border: none;
  padding: 8px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(244, 67, 54, 0.2);
  width: 36px;
  height: 36px;
}

.global-close-btn:hover {
  background: #d32f2f;
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(244, 67, 54, 0.3);
}

.close-icon {
  width: 20px;
  height: 20px;
}

.audio-progress-section {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-grow: 1;
  min-width: 250px;
}

.audio-time-display {
  font-size: 0.85rem;
  color: #555;
  font-weight: 500;
  min-width: 35px;
}

.audio-progress-container {
  flex-grow: 1;
  height: 32px;
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 10px 0;
  transition: all 0.2s ease;
}

.audio-progress-container:hover {
  transform: scaleY(1.1);
}

.audio-progress-bar {
  width: 100%;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  position: relative;
  border: 1px solid #ccc;
  transition: all 0.2s ease;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.1);
}

.audio-progress-container:hover .audio-progress-bar {
  height: 10px;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.1);
}

.audio-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #45a049);
  border-radius: 3px;
  transition: width 0.1s ease;
  position: relative;
}

.audio-progress-handle {
  width: 18px;
  height: 18px;
  background: #3f51b5;
  border: 3px solid white;
  border-radius: 50%;
  position: absolute;
  top: -5px;
  transform: translateX(-50%);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  z-index: 2;
  cursor: pointer;
  transition: all 0.2s ease;
  opacity: 0.9;
}

.audio-progress-container:hover .audio-progress-handle {
  opacity: 1;
  transform: translateX(-50%) scale(1.3);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
}

@media (max-width: 768px) {
  .daily-feed-content {
    grid-template-columns: 1fr;
    gap: 1.5rem;
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
  
  .subscription-manage-btn {
    padding: 0.6rem 1rem;
    font-size: 0.8rem;
    border-radius: 6px;
  }
  
  .manage-icon {
    width: 16px;
    height: 16px;
  }

  .audio-global-controls {
    bottom: 10px;
    padding: 8px 15px;
    border-radius: 15px;
    gap: 8px;
    flex-direction: row;
    flex-wrap: wrap;
    min-width: 320px;
    max-width: 95vw;
  }

  .global-play-pause-btn {
    width: 36px;
    height: 36px;
    padding: 8px;
  }

  .global-play-pause-btn .play-icon,
  .global-play-pause-btn .pause-icon {
    width: 18px;
    height: 18px;
  }

  .audio-progress-section {
    gap: 6px;
    flex: 1;
    min-width: 180px;
  }

  .audio-time-display {
    font-size: 0.75rem;
    min-width: 30px;
  }

  .audio-progress-container {
    height: 28px;
    padding: 8px 0;
  }

  .audio-progress-bar {
    height: 10px;
  }

  .audio-progress-handle {
    width: 20px;
    height: 20px;
    top: -5px;
  }

  .global-close-btn {
    width: 32px;
    height: 32px;
    padding: 6px;
  }

  .close-icon {
    width: 18px;
    height: 18px;
  }
}
</style> 