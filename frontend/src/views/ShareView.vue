<template>
  <div class="share-manager">
    <!-- 左侧：文件夹 -->
    <SharedSidebar
    :shares="shares"
      :papers-map="papersMap"     
      :current-user-id="userId"
      :activePaperId="selected ? selected.paper_id : null" 
      @select-folder="handleSelectFolder"
      @load-papers="handleLoadPapers" 
      @select="onSelectPaper" 
      @remove="handleRemove"
    />

   <div class="right-pane">
  <template v-if="activeId !== null">
    <div class="content-wrap">
      <!-- 3D 图：保持原样 -->
      <GraphWithDetail
        :papers="graphData"
        v-model="selected" 
        class="graph-detail"
      />

      <!-- 右侧垂直两栏 -->
      <div class="right-column">
        <!-- ① summary‑area：右上 -->
        
        <div class="summary-area">
          <div class="summary-header">
            <h3>Summary</h3>
            <button class="regen-btn"
                    :disabled="summaryLoading"
                    @click="generateSummary">
              {{ summaryText ? 'Regenerate' : 'Generate' }}
            </button>
          </div>

          <div v-if="summaryLoading" class="loading">Loading…</div>

          <!-- 有摘要 -->
          <div v-else-if="summaryText"
              class="summary-content"         
              v-html="renderedSummary">        
          </div>

          <!-- 无摘要 -->
          <div v-else class="no-summary">No summary yet.</div>
        </div>


        <!-- ② comment‑area：右下（原代码整体搬过来） -->
        <div class="comment-area">
          <h3>Comments</h3>

          <div class="comment-input-wrap">
            <textarea v-model="newComment"
                      placeholder="Leave a comment..."
                      class="comment-input">
            </textarea>
            <button :disabled="!newComment.trim()"
                    class="submit-btn"
                    @click="submitComment">
              Submit
            </button>
          </div>

          <ul class="comment-list">
            <li v-for="c in comments" :key="c.id">
              <div class="comment-author">
                {{ c.commenter_name }}:
                <button v-if="c.commenter_id === userId"
                        class="delete-btn"
                        @click="deleteComment(c.id)">
                  ✖
                </button>
              </div>
              <div class="comment-content">{{ c.content }}</div>
              <div class="comment-date">{{ formatDate(c.created_at) }}</div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </template>
    <div v-else class="empty-placeholder">
    Select a folder to view its papers.
  </div>
</div>
  </div>
</template>



<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount,computed,reactive } from 'vue'
import SharedSidebar   from '@/components/SharedSidebar.vue'
import GraphWithDetail from '@/components/GraphWithDetail.vue'
import api             from '@/services/api'
import MarkdownIt from 'markdown-it'
const md = new MarkdownIt({ linkify: true, breaks: true })
const papersMap = reactive<Record<number, Paper[]>>({})

/* ② 展开文件夹时：先拉论文列表，再激活它 */
async function handleLoadPapers(folderId: number) {
  if (!papersMap[folderId]) {
    papersMap[folderId] = await api.get_files_by_folderId(folderId)
  }
  activeId.value = folderId
}
function handleSelectFolder(fid:number) {
  activeId.value = fid                              // ① 更新右侧
  if (!papersMap[fid]) {                            // ② 若还没缓存
    handleLoadPapers(fid)                           //    立刻去拉
  }
  refreshRightPane(activeId.value!)
}

/* ③ 点击论文行：把它设为 selected（高亮用） */
function onSelectPaper(pid: string) {
  const file = papersMap[activeId.value!]?.find(f => f.paper_id === pid) || null
  selected.value = file
}

/* 响应式：把 summaryText ➜ HTML */
const renderedSummary = computed(() =>
  summaryText.value ? md.render(summaryText.value) : ''
)
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
  embedding?: number[]  // 可选的向量表示

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
  commenter_id: string
  created_at: string
}>>([])
const newComment = ref("")
const userId = localStorage.getItem('X-User-ID') || ''
/* ---------- 新增 state ---------- */
const summaryText   = ref<string | null>(null)
const summaryLoading = ref(false)

/* ---------- API 封装 ---------- */
async function fetchSummary(folderId: number) {
  summaryLoading.value = true
  try {
    summaryText.value = await api.get_summary(folderId)
  } catch {
    summaryText.value = null
    console.error('Failed to fetch summary')
  } finally {
    summaryLoading.value = false
  }
}

async function generateSummary() {
  if (!activeId.value) return
  summaryLoading.value = true
  try {
    summaryText.value = await api.regen_summary(activeId.value) // POST
  } catch {
    alert('Failed to generate summary')
  } finally {
    summaryLoading.value = false
  }
}


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


async function submitComment() {
  if (!activeId.value || !newComment.value.trim()) return
  const saved = await api.add_shared_comment(activeId.value,newComment.value)
  comments.value.push(saved)
  newComment.value = ""
}
async function deleteComment(cid: number) {
  if (!confirm('Delete this comment?')) return
  try {
    await api.delete_shared_comment(cid)
    comments.value = comments.value.filter(c => c.id !== cid)
  } catch (e) {
    alert('Failed to delete comment.')
  }
}
async function refreshRightPane(folderId: number) {
  /* ① 摘要 */
  await fetchSummary(folderId)

  /* ② 论文列表（先取缓存，没有就拉） */
  if (!papersMap[folderId]) {
    papersMap[folderId] = await api.get_files_by_folderId(folderId)
  }
  const files = papersMap[folderId]

  /* ③ 计算余弦 → citeMap → graphData （原来 watch 里的代码整段搬过来） */
  const citeMap = new Map<string, string[]>()
  const cosine = (a:number[], b:number[])=>{
    let dot=0,na=0,nb=0
    for(let i=0;i<a.length;i++){
      dot+=a[i]*b[i]; na+=a[i]*a[i]; nb+=b[i]*b[i]
    }
    return dot/(Math.sqrt(na)*Math.sqrt(nb)+1e-10)
  }
  for(let i=0;i<files.length;i++){
    const fi=files[i]; if(!fi.embedding) continue
    for(let j=i+1;j<files.length;j++){
      const fj=files[j]; if(!fj.embedding) continue
      if(cosine(fi.embedding,fj.embedding) > .93){
        ;(citeMap.get(fi.paper_id)??citeMap.set(fi.paper_id,[]).get(fi.paper_id)!).push(fj.paper_id)
        ;(citeMap.get(fj.paper_id)??citeMap.set(fj.paper_id,[]).get(fj.paper_id)!).push(fi.paper_id)
      }
    }
  }

  graphData.value = files.map(f=>({
    id:f.paper_id,size:10,link:f.pdf_url,
    cites:citeMap.get(f.paper_id)||[],
    categories:f.categories||[],authors:f.authors||[],
    published_date:f.published_date||'',abstract:f.abstract||'',
    pdf_url:f.pdf_url||'',paper_id:f.paper_id,title:f.title,
  }))

  /* ④ 评论 */
  await loadComments(folderId)
}

// --- 监听 activeId 变化，加载对应 papers ---
watch(
  activeId,
  async (id) => {
    selected.value = null

    if (id === null) {
      graphData.value = []
      summaryText.value = null
      return
    }
    await refreshRightPane(id)
  },
  { immediate: true }
)


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
  width: 90%;
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

  /* 让 padding + border 计入 width */
  box-sizing: border-box;

  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  color: #111827;

  box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
  transition: border 0.2s, box-shadow 0.2s;
  resize: vertical;
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
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  background: #f9fafb;
  overflow: hidden;
  min-height: 0;
}
.delete-btn {
  margin-left: .4rem;
  background: none;
  border: none;
  color: #ef4444;          /* 红 */
  cursor: pointer;
  font-size: .9rem;
  line-height: 1;
}
.delete-btn:hover {
  color: #b91c1c;
}

.right-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;          /* 关键：允许收缩 */
  border-left: 1px solid #e5e7eb;
}

/* summary‑area：高度随内容 */
.summary-area {
  padding: 1rem 1rem 0.5rem;
  background: #f8fafc;
  border-bottom: 1px solid #e5e7eb;
}
.summary-area h3 {
  margin: 0 0 0.4rem;
  font-size: 1.1rem;
  font-weight: 600;
}
.summary-area ul {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.9rem;
  color: #374151;
}
.summary-area li + li { margin-top: 0.25rem; }

/* comment‑area 保持原有样式（略） */
.right-pane .comment-area {
  flex: 1;                /* 填满剩余空间 */
  overflow: hidden;       /* 滚动由内部 comment-list 控制 */
}
.loading, .no-summary { color: #6b7280; font-size: 0.9rem; }

.summary-text {
  margin: 0 0 .8rem;
  white-space: pre-wrap;
  font-size: 0.93rem;
  line-height: 1.4;
  color: #374151;
}

.regen-btn {
  display: inline-block;
  padding: .3rem .8rem;
  font-size: .85rem;
  border: 1px solid #3b82f6;
  background: #3b82f6;
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: background .2s;
}
.regen-btn:hover:not(:disabled) { background: #2563eb; }
.regen-btn:disabled { opacity: .6; cursor: not-allowed; }
.summary-header{
  display: flex;
  align-items: center;
  justify-content: space-between;  /* h3 左，按钮右 */
}

/* h3 保持原来的 margin / 字体即可 */
.summary-area h3{
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

/* 如果需要让按钮更贴边，可给 summary-area 额外 padding-right */
.summary-area{
  padding: 1rem 1rem 0.5rem;   /* 上 右 下 左 */
}
/* 新增：限制高度、可滚动 */
.summary-content {
  max-height: 200px;       /* 你想要的可视高度 */
  overflow-y: auto;
  padding-right: 4px;      /* 给滚动条留一点空 */
}

</style>
