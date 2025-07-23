<template>
  <div class="share-manager">
    <!-- 左侧：文件夹 -->
    <SharedSidebar
      :shares="shares"
      :activeShareId="activeId"
      :currentUserId="userId"
      @select="onSelect"
      @remove="handleRemove"
      class="left-sidebar"
    />

    <!-- 右侧：图 + 详情 + 评论 -->
    <div class="right-pane">
      <template v-if="activeId !== null">
        <div class="content-wrap">
          <!-- 3D 图 -->
          <GraphWithDetail
            :papers="graphData"
            :selected="selected"
            class="graph-detail"
          />

          <!-- 评论区 -->
          <div class="comment-area">
            <h3>Comments</h3>

            <!-- 新评论输入 -->
            <div class="comment-input-wrap">
              <textarea
                v-model="newComment"
                placeholder="Leave a comment..."
                class="comment-input"
              ></textarea>
              <button
                class="submit-btn"
                :disabled="!newComment.trim()"
                @click="submitComment"
              >
                Submit
              </button>
            </div>

            <!-- 评论列表 -->
            <ul class="comment-list">
              <li v-for="c in comments" :key="c.id">
                <div class="comment-author">{{ c.commenter_name }}:</div>
                <div class="comment-content">{{ c.content }}</div>
                <div class="comment-date">
                  {{ formatDate(c.created_at) }}
                </div>
              </li>
            </ul>
          </div>
        </div>
      </template>

      <!-- 未选择文件夹时 -->
      <div v-else class="empty-placeholder">
        Select a folder to view its papers.
      </div>
  </div>
</div>
</template>



<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount,computed } from 'vue'
import SharedSidebar   from '@/components/SharedSidebar.vue'
import GraphWithDetail from '@/components/GraphWithDetail.vue'
import api             from '@/services/api'

// --- 类型定义 ---
interface ShareMeta {
  id: number
  folder_id: number
  owner_id: string
  is_public: boolean
  folder_name: string
  file_cnt: number
  created_at: string
}
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
function formatDate(timestamp: string): string {
  const d = new Date(timestamp)
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

// --- 响应式数据 ---
const shares   = ref<ShareMeta[]>([])
const activeId = ref<number|null>(null)
const graphData = ref<Paper[]>([])
const selected = ref<Paper|null>(null)
const comments = ref<Array<{
  id: number
  content: string
  commenter_name: string
  created_at: string
}>>([])
const newComment = ref("")
const userId = localStorage.getItem('X-User-ID') || ''

// --- 加载分享列表 ---
async function loadShares() {
  shares.value = await api.get_shared_folders()
}
async function loadComments(folderId: number) {
  comments.value = await api.get_shared_comments(folderId)
}

// --- 删除分享 ---
async function handleRemove(folderId: number) {
  if (confirm('Delete this shared folder?')) {
    await api.delete_shared_folder(folderId)
    await loadShares()
    // 如果删除的正是当前 active，清空右侧
    if (activeId.value === folderId) activeId.value = null
  }
}

// --- 选中左侧文件夹 ---
function onSelect(id: number) {
  activeId.value = id

}
async function submitComment() {
  if (!activeId.value || !newComment.value.trim()) return
  const saved = await api.add_shared_comment(activeId.value,newComment.value)
  comments.value.push(saved)
  newComment.value = ""
}

// --- 监听 activeId 变化，加载对应 papers ---
watch(activeId, async (id) => {
  selected.value = null
  if (id === null) {
    graphData.value = []
  } else {
    // 假设后端接口：api.get_files_by_folderId(folderId)
    const files = await api.get_files_by_folderId(id)
    // 将返回的文件对象映射成 Paper
    graphData.value = files.map((f: any) => ({
      id: f.paper_id,
      size: 10,               // 统一大小，或 f.size 字段
      link: f.pdf_url,
      cites: [],               // 如果有引用关系可填这里
      categories: f.categories || [],
      authors: f.authors || [],
      published_date: f.published_date || '',
      abstract: f.abstract || '',
      pdf_url: f.pdf_url || '',
      paper_id: f.paper_id,
      title: f.title,
    }))
    await loadComments(id)
  }
}, { immediate: true })

// --- 生命周期钩子 ---
onMounted(() => {
  loadShares()
  window.addEventListener('share-folder-success', loadShares)
})
onBeforeUnmount(() => {
  window.removeEventListener('share-folder-success', loadShares)
})
</script>

<style scoped>



.comment-area h3 {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
  color: #333;
  font-weight: 600;
}

.comment-input-wrap {
  display: flex;
  flex-direction: column;
  margin-bottom: 1rem;
}

.comment-input {
  width: 100%;
  min-height: 80px;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 0.5rem;
  font-size: 0.95rem;
  resize: vertical;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
}

.submit-btn {
  align-self: flex-end;
  margin-top: 0.5rem;
  padding: 0.4rem 0.8rem;
  background: #2563eb; /* 蓝色按钮 */
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.submit-btn:hover {
  background: #1d4ed8;
}

.comment-list {
  flex: 1;
  overflow-y: auto;
  list-style: none;
  padding: 0;
  margin: 0;
}

.comment-list li {
  background: #fff;
  padding: 0.6rem 0.8rem;
  margin-bottom: 0.5rem;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.comment-author {
  font-weight: 600;
  font-size: 0.9rem;
  color: #111827;
  margin-bottom: 0.2rem;
}

.comment-content {
  font-size: 0.88rem;
  color: #4b5563;
  word-break: break-word;
}
.empty-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
}
.comment-input {
  width: 100%;
  min-height: 80px;
  max-height: 200px;
  padding: 0.75rem 1rem;
  font-size: 0.95rem;
  border: 1px solid #d1d5db; /* 灰色边框 */
  border-radius: 8px;         /* 更圆润 */
  background: #fff;
  color: #111827;              /* 深色文字 */

  box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
  transition: border 0.2s, box-shadow 0.2s;
  resize: vertical;            /* 支持上下拖动，控制范围 */
}

/* 聚焦时：更明显的边框 + 阴影 */
.comment-input:focus {
  outline: none;
  border-color: #3b82f6;       /* 蓝色高亮边 */
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

/* placeholder 优化 */
.comment-input::placeholder {
  color: #9ca3af;               /* 淡灰提示词 */
  font-style: italic;
}
.share-manager {
  display: flex;
  height: calc(100vh - 4rem);
}

/* 左侧不变 */
.left-sidebar {
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid #e5e7eb;
  /* 保证满高 */
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 右侧要能在竖向上缩小 */
.right-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;   /* 关键：允许向下收缩 */
}

/* content-wrap：横向两列，也要允许收缩 */
.content-wrap {
  display: flex;
  flex: 1;
  min-height: 0;  /* 关键：让下面的 graph-detail 可以收缩 */
}

/* graph-detail（放 3D 图的地方） */
.graph-detail {
  flex: 2;
  overflow: hidden;
  min-height: 0;  /* 关键：允许它收缩到父级给的高度 */
}

/* comment-area 保持原样，但也加上 min-height:0 */
.comment-area {
  flex: 1;
  border-left: 1px solid #e5e7eb;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  background: #f9fafb;
  overflow: hidden;
  min-height: 0;
}

</style>
