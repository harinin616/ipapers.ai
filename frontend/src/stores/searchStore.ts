import { reactive } from 'vue'

interface SearchState {
  query: string
  results: any[]
  hasSearched: boolean
  sortBy: string
  summary: string | null
  includeSummary: boolean
  isSummaryLoading: boolean
  summaryError: string | null
}

const searchState = reactive<SearchState>({
  query: '',
  results: [],
  hasSearched: false,
  sortBy: 'relevance',
  summary: null,
  includeSummary: false,
  isSummaryLoading: false,
  summaryError: null
})

export const searchStore = {
  // Getters
  getQuery: () => searchState.query,
  getResults: () => searchState.results,
  getHasSearched: () => searchState.hasSearched,
  getSortBy: () => searchState.sortBy,
  getSummary: () => searchState.summary,
  getIncludeSummary: () => searchState.includeSummary,
  getIsSummaryLoading: () => searchState.isSummaryLoading,
  getSummaryError: () => searchState.summaryError,

  setSortBy: (sortBy: string) => {
    searchState.sortBy = sortBy
  },

  setIncludeSummary: (includeSummary: boolean) => {
    searchState.includeSummary = includeSummary
  },

  setIsSummaryLoading: (loading: boolean) => {
    searchState.isSummaryLoading = loading
  },

  setSummaryError: (error: string | null) => {
    searchState.summaryError = error
  },
  
  // Actions
  setQuery: (query: string) => {
    searchState.query = query
  },
  
  setResults: (results: any[]) => {
    searchState.results = results
    searchState.hasSearched = true
  },

  setSummary: (summary: string | null) => {
    searchState.summary = summary
  },
  
  clearSearch: () => {
    searchState.query = ''
    searchState.results = []
    searchState.hasSearched = false
    searchState.summary = null
    searchState.isSummaryLoading = false
    searchState.summaryError = null
  },
  
  // Check if we have cached results for a query
  hasCachedResults: (query: string) => {
    return searchState.hasSearched && 
           searchState.query === query && 
           searchState.results.length > 0
  }
} 