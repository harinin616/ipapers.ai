<template>
  <div class="search-container">
    <div class="search-form">
      <input 
        v-model="localSearchQuery" 
        class="search-input" 
        :placeholder="dynamicPlaceholder" 
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
        <span v-if="isLoading && searchWithSummary">Searching...</span>
        <span v-else>Search</span>
      </button>
    </div>
  </div>
</template>

<script>
// 按你的项目实际情况替换导入：api.function名字
// 例如：import { getPaperCount } from '@/api/papers'
import api from '@/services/api'

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
    // 作为后备占位符（当后端不可用时用）
    placeholder: {
      type: String,
      default: 'Search papers...'
    }
  },
  emits: ['update:modelValue', 'search'],
  data() {
    return {
      searchWithSummary: false,
      dynamicPlaceholder: 'Search papers...' // 初始化，待后端返回后替换
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
    async loadPaperCount() {
      try {
        // 如果你是 api.function名字()，就把下一行改成：const count = await api.function名字()
        const count = await api.countPapers();
        const n = Number(count);
        const pretty = Number.isFinite(n) ? n.toLocaleString() : '**';
        this.dynamicPlaceholder = `Search ${pretty} papers from all fields of science.`;
      } catch (e) {
        // 失败则退回到 props.placeholder
        this.dynamicPlaceholder = this.placeholder || 'Search papers...';
      }
    },
    handleSearch(includeSummary = false) {
      if (this.localSearchQuery.trim()) {
        this.searchWithSummary = includeSummary;
        this.$emit('search', this.localSearchQuery.trim(), includeSummary);
      }
    }
  },
  mounted() {
    // 组件挂载后拉取后端数量
    this.loadPaperCount();
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
  background-color: #3b82f6;
  border-left: 1px solid #fff;
  border-radius: 0 4px 4px 0;
}

.search-button-ai:hover {
  background-color: #2563eb;
}

.search-button-ai:disabled {
  background-color: #bfdbfe;
}
</style>
