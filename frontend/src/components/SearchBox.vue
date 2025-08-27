<template>
  <div class="search-container">
    <div class="search-form">
      <input 
        v-model="localSearchQuery" 
        class="search-input" 
        :placeholder="placeholder" 
        @keyup.enter="handleSearch(true)"
        aria-label="Search papers"
      />
      <!-- Normal search button (hidden but code preserved) -->
      <button 
        @click="handleSearch(false)" 
        class="search-button search-button-hidden" 
        :disabled="isLoading || !localSearchQuery.trim()"
        style="display: none;"
      >
        <span v-if="isLoading && !searchWithSummary">Searching...</span>
        <span v-else>🔍 Search</span>
      </button>
      <button 
        @click="handleSearch(true)" 
        class="search-button search-button-ai" 
        :disabled="isLoading || !localSearchQuery.trim()"
      >
        <span v-if="isLoading && searchWithSummary">🤖 AI Search...</span>
        <span v-else>🤖 AI Search</span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SearchBox',
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    isLoading: {
      type: Boolean,
      default: false
    },
    placeholder: {
      type: String,
      default: 'Search papers...'
    }
  },
  emits: ['update:modelValue', 'search'],
  data() {
    return {
      searchWithSummary: false
    }
  },
  computed: {
    localSearchQuery: {
      get() {
        return this.modelValue;
      },
      set(value) {
        this.$emit('update:modelValue', value);
      }
    }
  },
  methods: {
    handleSearch(includeSummary = false) {
      if (this.localSearchQuery.trim()) {
        this.searchWithSummary = includeSummary;
        this.$emit('search', this.localSearchQuery.trim(), includeSummary);
      }
    }
  }
}
</script>

<style scoped>
.search-container {
  background-color: white;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.search-form {
  display: flex;
}

.search-input {
  flex: 1;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px 0 0 4px;
  outline: none;
}

.search-input:focus {
  border-color: #3f51b5;
}

.search-button {
  padding: 0.75rem 1rem;
  background-color: #3f51b5;
  color: white;
  border: none;
  border-radius: 0;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
  white-space: nowrap;
  min-width: 100px;
}

.search-button:first-of-type {
  border-radius: 0;
}

.search-button:last-of-type {
  border-radius: 0 4px 4px 0;
}

.search-button:hover {
  background-color: #303f9f;
}

.search-button:disabled {
  background-color: #c5cae9;
  cursor: not-allowed;
}

.search-button-ai {
  background-color: #ff6b35;
  border-left: 1px solid #fff;
  border-radius: 0 4px 4px 0;
}

.search-button-ai:hover {
  background-color: #e55a2b;
}

.search-button-ai:disabled {
  background-color: #ffccb3;
}
</style> 