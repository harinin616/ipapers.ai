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
          <!-- 图 -->
          <GraphWithDetail :papers="graphData" class="graph-detail" />
          
          <!-- 评论区 -->
          <div class="comment-area">
            <h3>Comments</h3>
            <textarea placeholder="Leave a comment..." class="comment-input"></textarea>
            <button class="submit-btn">Submit</button>
            <ul class="comment-list">
              <li>Example comment 1</li>
              <li>Example comment 2</li>
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
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
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
interface Paper {
  id: string
  label: string
  size: number
  link?: string
  cites?: string[]
}

// --- 响应式数据 ---
const shares   = ref<ShareMeta[]>([])
const activeId = ref<number|null>(null)
const graphData = ref<Paper[]>([])
const userId = localStorage.getItem('X-User-ID') || ''

// --- 加载分享列表 ---
async function loadShares() {
  shares.value = await api.get_shared_folders()
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

// --- 监听 activeId 变化，加载对应 papers ---
watch(activeId, async (id) => {
  if (id === null) {
    graphData.value = []
  } else {
    // 假设后端接口：api.get_files_by_folderId(folderId)
    const files = await api.get_files_by_folderId(id)
    // 将返回的文件对象映射成 Paper
    graphData.value = files.map((f: any) => ({
      id: f.paper_id,
      label: f.filename,
      size: 10,               // 统一大小，或 f.size 字段
      link: f.paper_URL,
      cites: []               // 如果有引用关系可填这里
    }))
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
.share-manager {
  display: flex;
  height: calc(100vh - 4rem);
}

.left-sidebar {
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid #e5e7eb;
}

.right-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 内容区域：图 + 评论 */
.content-wrap {
  display: flex;
  flex: 1;
}

/* 图（左边） */
.graph-detail {
  flex: 2;   /* 或者 flex: auto; 控制比例 */
  overflow: hidden; /* 保证不会溢出 */
}
.comment-area {
  flex: 1;
  border-left: 1px solid #e5e7eb;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  background: #f9fafb;  /* 淡灰背景 */
  overflow: hidden;
}

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

</style>
