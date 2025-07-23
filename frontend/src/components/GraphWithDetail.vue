<template>
  <div class="col-wrap">
    <!-- 上 40%：3D 图，双向绑定 selected -->
    <div class="graph-area">
      <SharedGraph3D
        v-model="localSelected"
        :papers="papers"
      />
    </div>

    <!-- 下 60%：detail-area -->
    <div class="detail-area">
      <div v-if="!localSelected " class="placeholder">
        Click a node above to see details here.
      </div>
      <div v-else class="selected-detail">
        <div class="paper-detail">
          <!-- 可点击标题 -->
          <h2 class="paper-title">
            <a
              :href="localSelected.pdf_url"
              target="_blank"
              rel="noopener"
            >
              {{ localSelected .title }}
            </a>
          </h2>

          <!-- 发布日期 -->
          <p class="paper-date">
            Published: {{ formattedDate }}
          </p>

          <!-- 作者列表 -->
          <p class="paper-authors">
            <strong>Authors:</strong> {{ localSelected .authors.join(', ') }}
          </p>

          <!-- 摘要 -->
          <div class="paper-abstract">
            {{ localSelected.abstract }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch} from 'vue'
import SharedGraph3D from '@/components/SharedGraph3D.vue'

export interface Paper {
  link?: string
  cites?: string[] 

  id: string
  size: number
  paper_id: string
  title: string
  pdf_url: string
  abstract: string
  authors: string[]
  categories: string[]
  published_date: string
}

const props = defineProps<{ papers: Paper[] ,selected: Paper|null }>()
const localSelected = ref<Paper|null>(props.selected)

const formattedDate = computed(() => {
  if (!localSelected.value) return ''
  const d = new Date(localSelected.value.published_date)
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',   // February
    day: 'numeric',  // 24
  })
})
watch(
  () => props.papers,
  () => { localSelected.value = null }
)
</script>
<style scoped>
.col-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;         /* 改成 100% */
  min-height: 0;         /* 确保整屏高度 */
  margin: 0;
}

.graph-area {
  flex: 0 0 60%;          /* 上 40% */
  min-height: 0;          /* 防止子元素撑高溢出 */
}

.detail-area {
  flex: 0 0 40%;          /* 下 60% */
  /* 不在这里滚动 */
  overflow: hidden;
  background: #f9fafb;
  padding: 1rem;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
}

/* “空状态” 占满整个 detail-area */
.placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
}

/* 让这个容器撑满 detail-area，并自己滚动 */
.selected-detail {
  flex: 1;
  overflow-y: auto;       /* 这里才出现滚动条 */
  overflow-x: hidden;
}


/* 3D 图满铺 */
.graph-area > * {
  width: 100%;
  height: 100%;
}


.paper-detail {
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 1.5rem;
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

/* 标题链接 */
.paper-title {
  margin: 0 0 0.5rem;
  font-size: 1.5rem;
  line-height: 1.2;
}
.paper-title a {
  color: #2563eb;
  text-decoration: none;
}
.paper-title a:hover {
  text-decoration: underline;
}

/* 发布日期 */
.paper-date {
  margin: 0 0 0.75rem;
  font-size: 0.9rem;
  color: #6b7280;
}

/* 作者 */
.paper-authors {
  margin: 0 0 1rem;
  font-size: 1rem;
  color: #374151;
}

/* 摘要 */
.paper-abstract {
  line-height: 1.6;
  color: #4b5563;
  white-space: pre-wrap;
}
</style>
