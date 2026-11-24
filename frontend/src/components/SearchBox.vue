<template>
  <div class="search-container">
    <form class="search-form" role="search" @submit.prevent="handleSearch(true)">
      <svg class="search-icon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
      <input
        v-model="localSearchQuery"
        class="search-input"
        type="search"
        :placeholder="dynamicPlaceholder"
        aria-label="Search papers"
        autocomplete="off"
      />
      <button
        type="submit"
        class="search-button search-button-ai"
        :disabled="isLoading || !localSearchQuery.trim()"
      >
        <span v-if="isLoading && searchWithSummary">Searching…</span>
        <span v-else>Search</span>
      </button>
    </form>
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
.search-container { max-width: 680px; margin: 0 auto; }
.search-form {
  display: flex; align-items: center; gap: var(--sp-2);
  padding: 6px 6px 6px var(--sp-4);
  background: var(--surface); border: 1px solid var(--border-strong);
  border-radius: var(--r-pill); box-shadow: var(--shadow-2);
  transition: border-color .15s, box-shadow .15s;
}
.search-form:focus-within { border-color: var(--accent); box-shadow: var(--shadow-2), var(--ring); }
.search-icon { color: var(--text-3); flex: none; }
.search-input {
  flex: 1; min-width: 0; height: 40px; padding: 0 var(--sp-2);
  font: var(--fs-md)/1 var(--font-sans); color: var(--text);
  background: transparent; border: none; outline: none; box-shadow: none;
  -webkit-appearance: none; appearance: none;
}
.search-input::placeholder { color: var(--text-3); }
.search-input::-webkit-search-cancel-button { -webkit-appearance: none; }
.search-button {
  flex: none; height: 40px; padding: 0 var(--sp-5);
  font: 600 var(--fs-sm)/1 var(--font-sans); color: var(--accent-ink);
  background: var(--accent); border: none; border-radius: var(--r-pill);
  cursor: pointer; white-space: nowrap; transition: background .15s, transform .05s;
}
.search-button:hover { background: var(--brand-600); color: #fff; }
.search-button:active { transform: translateY(1px); }
.search-button:disabled { opacity: .45; cursor: not-allowed; }
@media (max-width: 520px) { .search-button { padding: 0 var(--sp-4); } }
</style>
