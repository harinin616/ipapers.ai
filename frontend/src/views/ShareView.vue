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
      @update-mode="handleUpdateMode"
    />

    <!-- 右侧整体面板 -->
    <div class="right-pane">
      <template v-if="activeId !== null">
        <div class="content-wrap">
          <!-- 主列：图 + 摘要 -->
          <div class="main-column">
            <div class="graph-area">
            <SharedGraph3D
               ref="graphRef"
               v-model="selected"
               :papers="graphData"
                @node-click="detailPaper = $event"
               class="graph-detail"
             />
          </div>

            <!-- 摘要放在图下方 -->
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
              <div v-else-if="summaryText" class="summary-content" v-html="renderedSummary"></div>
              <div v-else class="no-summary">No summary yet.</div>
            </div>
          </div>

          <!-- 侧栏：仅评论区域 -->
          <div class="comment-area">
            <h3>Comments</h3>
            <div class="comment-input-wrap">
              <textarea v-model="newComment"
                        placeholder="Leave a comment..."
                        class="comment-input"></textarea>
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
      </template>
      <div v-else class="empty-placeholder">
        Select a folder to view its papers.
      </div>
    </div>


     <transition name="overlay-fade">
      <div
        v-if="detailPaper"
        class="modal-overlay"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="'modal-title'"
        @click.self="closeDetail"
      >
        <transition name="modal-slide">
          <div
            class="modal-content"
            tabindex="-1"
            ref="modalContent"
          >
            <header class="modal-header">
              <h2 id="modal-title">{{ detailPaper.title }}</h2>
              <button
                class="close-btn"
                @click="closeDetail"
                aria-label="Close"
              >✖</button>
            </header>
            <section class="modal-body" id="modal-desc">
              <p><strong>Authors:</strong> {{ detailPaper.authors.join(', ') }}</p>
              <p><strong>Published:</strong> {{ formatDate(detailPaper.published_date) }}</p>
              <p><strong>Abstract:</strong></p>
              <p>{{ detailPaper.abstract }}</p>
              <a :href="detailPaper.pdf_url" target="_blank">View PDF</a>
            </section>
          </div>
        </transition>
      </div>
    </transition>
  </div>

</template>



<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount,computed,reactive } from 'vue'
import SharedSidebar   from '@/components/SharedSidebar.vue'
import GraphWithDetail from '@/components/GraphWithDetail.vue'
import SharedGraph3D   from '@/components/SharedGraph3D.vue'
import api             from '@/services/api'
import MarkdownIt from 'markdown-it'
const md = new MarkdownIt({ linkify: true, breaks: true })
const papersMap = reactive<Record<number, Paper[]>>({})
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const props = defineProps<{ folderId: number | null }>()

/* ② 用它初始化 activeId */
const activeId = ref<number | null>(props.folderId)

/* ③ 监听 prop 变化（浏览器前进/后退、地址栏手改等） */
watch(
  () => props.folderId,
  fid => {
    if (fid === activeId.value) return
    if (fid) { handleSelectFolder(fid) }
    else     { activeId.value = null }
  },
  { immediate: true }
)
/* ② 展开文件夹时：先拉论文列表，再激活它 */
async function handleLoadPapers(folderId: number) {
  if (!papersMap[folderId]) {
    papersMap[folderId] = await api.get_files_by_folderId(folderId)
  }
  activeId.value = folderId
}
async function handleSelectFolder(fid:number) {                              // ① 更新右侧
  if (!papersMap[fid]) {                            // ② 若还没缓存
    await handleLoadPapers(fid)                           //    立刻去拉
  }                // ③ 刷新右侧内容
  activeId.value = fid
  const newUrl = `/rwf/${fid}`
  window.history.pushState(null, '', newUrl)
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
  try {
    console.log('Loading comments for folder:', folderId)
    comments.value = await api.get_shared_comments(folderId)
    console.log('Loaded comments:', comments.value)
  } catch (e) {
    console.error('Failed to load comments:', e)
    comments.value = []
  }
}

async function handleUpdateMode(p: { folder_id: number; is_public: boolean }) {
  await api.updateShareMode(p.folder_id, p.is_public)
}

// --- 删除分享 ---
async function handleRemove(folderId: number) {
    await api.delete_shared_folder(folderId)
    await loadShares()
    // 如果删除的正是当前 active，清空右侧
    if (activeId.value === folderId) activeId.value = null
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
      if(cosine(fi.embedding,fj.embedding) > .96){
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
const graphRef = ref<any>(null)
const detailPaper = ref<Paper|null>(null)



onMounted(() => {
  if (graphRef.value && typeof graphRef.value.onNodeClick === 'function') {
    graphRef.value.onNodeClick((n: any) => {
      // 只打开详情，不修改 selected
      detailPaper.value = n.paper || null
    })
  }
})

// 关闭弹窗
function closeDetail() {
  detailPaper.value = null
}


// --- 生命周期钩子 ---
onMounted(async () => {
    window.addEventListener('popstate', await onPopState)
  await loadShares()
  const fid = Number(route.params.folderId)
  if (fid) {
    await handleSelectFolder(fid)
  }
  window.addEventListener('share-folder-success', loadShares)
})
onBeforeUnmount(() => {
  window.removeEventListener('share-folder-success', loadShares)
})
onBeforeUnmount(() => {
  window.removeEventListener('popstate', onPopState)
})
  
async function onPopState() {
  const fid = Number(location.pathname.split('/').pop())
  if (fid) await handleSelectFolder(fid)
  else activeId.value = null
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && detailPaper.value) {
    closeDetail()
  }
}

watch(detailPaper, async (val) => {
  if (val) {
    // 开弹窗时 lock scroll
    document.body.style.overflow = 'hidden'
    await nextTick()
    // 焦点移到弹窗
    (modalContent.value as HTMLElement)?.focus()
  } else {
    // 关弹窗时恢复
    document.body.style.overflow = ''
  }
})

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})

const modalContent = ref<HTMLElement|null>(null)
</script>
<style scoped>
.share-manager {
  display: flex;
  height: calc(100vh - 4rem);
}

/* 左侧不变 */
.left-sidebar {
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* 右侧整体：垂直布局，允许收缩 */
.right-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* content-wrap：横向两列 主列 + 评论 */
.content-wrap {
  display: flex;
  flex: 1;
  min-height: 0;
}

/* 主列：graph + summary */
.main-column {
  flex: 2;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* 3D 图区域 */
.graph-detail {
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

/* 摘要区域：紧跟图下方 */
.summary-area {
  padding: 1rem;
  background: #f8fafc;
  border-top: 1px solid #e5e7eb;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.regen-btn {
  padding: .3rem .8rem;
  border: 1px solid #3b82f6;
  background: #3b82f6;
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: background .2s;
}

.regen-btn:hover:not(:disabled) { background: #2563eb; }
.regen-btn:disabled { opacity: .6; cursor: not-allowed; }

.summary-content {
  max-height: 200px;
  overflow-y: auto;
  margin-top: .5rem;
}

.loading, .no-summary {
  color: #6b7280;
  font-size: 0.9rem;
}

/* 评论区域：单列 */
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

.comment-input-wrap {
  display: flex;
  flex-direction: column;
  margin-bottom: 1rem;
}

.comment-input {
  width: 100%;
  min-height: 80px;
  padding: 0.75rem 1rem;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  resize: vertical;
  transition: border .2s, box-shadow .2s;
}

.comment-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
}

.submit-btn {
  align-self: flex-end;
  margin-top: 0.5rem;
  padding: 0.4rem 0.8rem;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
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
  margin-bottom: 0.2rem;
}

.delete-btn {
  margin-left: 0.4rem;
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
}

.delete-btn:hover {
  color: #b91c1c;
}

.empty-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
}


.share-manager {
  display: flex;
  height: calc(100vh - 4rem);
}

/* 左侧 Sidebar：固定宽度，带滚动 */
.share-manager > *:first-child {
  flex: 0 0 auto;
  border-right: 1px solid #e5e7eb;
  overflow-y: auto;
}

/* 右侧整体面板 */
.right-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* 内容区域：主区 + 评论 */
.content-wrap {
  flex: 1;
  display: flex;
  min-height: 0;
}

/* 主列：图 + 摘要 */
.main-column {
  flex: 3;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* 图区域：占满剩余空间 */
.graph-area {
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

/* 摘要区域：固定高度下滑动 */
.summary-area {
  flex: 0 0 auto;
  max-height: 300px;
  overflow-y: auto;
  padding: 1rem;
  background: #f8fafc;
  border-top: 1px solid #e5e7eb;
}

/* 评论区域：固定宽度，纵向布局 */
.comment-area {
  flex: 0 0 300px;
  border-left: 1px solid #e5e7eb;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  background: #f9fafb;
  overflow-y: auto;
}
.comment-area {
  min-width: 300px;    /* 被压缩到极窄时仍保持 300px */
  position: relative;  /* 建立新层级 */
  z-index: 20;         /* 把 canvas 压在下面 */
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-content {
  background: #fff;
  width: 80%;
  max-width: 600px;
  max-height: 90%;
  overflow-y: auto;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.2);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;
}
.close-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
}
.modal-body {
  padding: 1rem;
  line-height: 1.6;
}
.overlay-fade-enter-active,
.overlay-fade-leave-active {
  transition: opacity .3s;
}
.overlay-fade-enter-from,
.overlay-fade-leave-to {
  opacity: 0;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

/* 弹窗滑入 */
.modal-slide-enter-active {
  animation: slideIn .3s ease-out forwards;
}
.modal-slide-leave-active {
  animation: slideOut .2s ease-in forwards;
}
@keyframes slideIn {
  from { transform: translateY(20px); opacity: 0; }
  to   { transform: translateY(0);     opacity: 1; }
}
@keyframes slideOut {
  from { transform: translateY(0);     opacity: 1; }
  to   { transform: translateY(20px); opacity: 0; }
}

/* 弹窗主体 */
.modal-content {
  background: #fff;
  width: 90%;
  max-width: 600px;
  max-height: 85%;
  overflow-y: auto;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.25);
  outline: none; /* focus 时外观自行定义 */
}

/* 头部 */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}
.close-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: #555;
  transition: color .2s;
}
.close-btn:hover {
  color: #111;
}

/* 内容 */
.modal-body {
  padding: 1rem 1.5rem;
  line-height: 1.6;
}

/* 小屏下全屏弹窗 */
@media (max-width: 480px) {
  .modal-content {
    width: 100%;
    height: 100%;
    border-radius: 0;
    max-height: 100%;
  }
}
.overlay-fade-enter-active,
.overlay-fade-leave-active {
  transition: opacity .3s;
}
.overlay-fade-enter-from,
.overlay-fade-leave-to {
  opacity: 0;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

/* 弹窗滑入 */
.modal-slide-enter-active {
  animation: slideIn .3s ease-out forwards;
}
.modal-slide-leave-active {
  animation: slideOut .2s ease-in forwards;
}
@keyframes slideIn {
  from { transform: translateY(20px); opacity: 0; }
  to   { transform: translateY(0);     opacity: 1; }
}
@keyframes slideOut {
  from { transform: translateY(0);     opacity: 1; }
  to   { transform: translateY(20px); opacity: 0; }
}

/* 弹窗主体 */
.modal-content {
  background: #fff;
  width: 90%;
  max-width: 600px;
  max-height: 85%;
  overflow-y: auto;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.25);
  outline: none; /* focus 时外观自行定义 */
}

/* 头部 */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}
.close-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: #555;
  transition: color .2s;
}
.close-btn:hover {
  color: #111;
}

/* 内容 */
.modal-body {
  padding: 1rem 1.5rem;
  line-height: 1.6;
}

/* 小屏下全屏弹窗 */
@media (max-width: 480px) {
  .modal-content {
    width: 100%;
    height: 100%;
    border-radius: 0;
    max-height: 100%;
  }
}
.modal-content {
  background: #ffffff;
  width: 90%;
  max-width: 600px;
  max-height: 85%;
  overflow-y: auto;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.15);
  display: flex;
  flex-direction: column;
  font-family: 'Helvetica Neue', Arial, sans-serif;
}

/* 头部 */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e2e8f0;
  background: #f7fafc;
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
}
.modal-header h2 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
  color: #2d3748;
  line-height: 1.2;
}
.close-btn {
  width: 32px; height: 32px;
  font-size: 1.25rem;
  color: #4a5568;
  transition: color .2s, background .2s;
  border-radius: 4px;
}
.close-btn:hover {
  color: #e53e3e;
  background: rgba(229,62,62,0.1);
}

/* 正文 */
.modal-body {
  padding: 1.5rem;
  color: #4a5568;
  line-height: 1.6;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.modal-body p {
  margin: 0;
  font-size: 1rem;
}
.modal-body p + p {
  margin-top: 0.75rem;
}
.modal-body strong {
  color: #2b6cb0;
}

/* 作者、发表信息 */
.modal-body > p:first-child,
.modal-body > p:nth-child(2) {
  font-size: 0.95rem;
  color: #718096;
}
.modal-body > p:first-child strong,
.modal-body > p:nth-child(2) strong {
  color: #2d3748;
}

/* 链接按钮化 */
.modal-body a {
  display: inline-block;
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  background: #2b6cb0;
  color: #fff;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.9rem;
  transition: background .2s;
}
.modal-body a:hover {
  background: #2573b4;
}

/* 小屏下全屏 */
@media (max-width: 480px) {
  .modal-content {
    width: 100%;
    height: 100%;
    max-height: 100%;
    border-radius: 0;
  }
}
.right-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* 内容区：左右两栏 */
.content-wrap {
  display: flex;
  flex: 1;
  min-height: 0; /* 允许子元素收缩 */
}

/* 主列：上下两段 */
.main-column {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0; /* 允许图区域收缩 */
}

/* 强制画布铺满 graph-area */
.graph-area canvas,
.graph-area .graph-detail {
  width: 100% !important;
  height: 100% !important;
  display: block;
}

/* 底部摘要：固定高度，可自行调 */
.summary-area {
  flex: 0 0 300px; /* 固定 200px，高度可以自行调整 */
  overflow-y: auto;
  border-top: 1px solid #e5e7eb;
  background: #f8fafc;
}
.graph-area {
  flex: 1;
  min-width: 0;        /* 允许被压缩 */
  min-height: 0;
  overflow: hidden;
  position: relative;  /* ➜ canvas 的绝对定位以此为界 */
  z-index: 0;          /* 保证在 comment-area 之下 */
}

/* 让 3D 画布最多占满自己，不再保留老宽度 */
.graph-area canvas {
  position: absolute !important; /* ForceGraph3D 自己就是 absolute */
  inset: 0;                      /* 铺满父容器 */
  width: 100%  !important;
  height: 100% !important;
  max-width: 100%;
}
/* 把内容两栏改成网格：左自适应，右固定 300px */
.content-wrap{
  display: grid;
  grid-template-columns: 1fr 300px;  /* 300 可调 */
  width: 100%;
  min-width: 0;   /* 关键：允许整体收缩 */
  min-height: 0;  /* 允许子元素再收缩 */
}

/* 主列、评论列都要能收缩或固定 */
.main-column { min-width: 0; overflow: hidden; }
.comment-area{
  min-width: 0;          /* grid 已固定宽，再加一次保险 */
  overflow-y: auto;      /* 纵向滚动 */
}

</style>