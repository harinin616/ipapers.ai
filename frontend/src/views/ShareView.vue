<template>
  <div class="share-manager">
    <!-- 左侧：文件夹 -->
    <div class="sidebar-container">
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
        @sidebar-collapsed="(collapsed: boolean) => isSidebarCollapsed = collapsed"
      />
      <!-- 右侧拖拽手柄：只在非折叠状态显示 -->
      <div 
        v-show="!isSidebarCollapsed"
        class="sidebar-resize-handle"
        @mousedown="startSidebarResize"
        title="Drag to resize sidebar"
      ></div>
    </div>

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
                @node-click="handleNodeClick($event)"
               class="graph-detail"
             />
          </div>

            <!-- 摘要和推荐区域 -->
            <div class="bottom-area" :style="{ height: bottomAreaHeight + 'px' }">
              <!-- 拖拽调整手柄 -->
              <div 
                class="resize-handle-horizontal"
                @mousedown="startResize"
                title="Drag to resize"
              ></div>
              <!-- 标签页导航 -->
              <div class="tab-nav">
                <button 
                  class="tab-btn" 
                  :class="{ active: activeTab === 'summary' }"
                  @click="activeTab = 'summary'"
                >
                  Summary
                </button>
                <button 
                  class="tab-btn" 
                  :class="{ active: activeTab === 'recommendations' }"
                  @click="activeTab = 'recommendations'"
                >
                  Recommendations
                </button>
              </div>

              <!-- 标签页内容 -->
              <div class="tab-content">
                <!-- Summary Tab -->
                <div v-if="activeTab === 'summary'" class="summary-section">
                  <div class="section-header">
                <button class="regen-btn"
                        :disabled="summaryLoading"
                        @click="generateSummary">
                  {{ summaryText ? 'Regenerate' : 'Generate' }}
                </button>
              </div>
              <div v-if="summaryLoading" class="loading">Loading…</div>
              <div v-else-if="summaryText" class="summary-content" v-html="renderedSummary"></div>
                  <div v-else class="no-content">No summary yet.</div>
                </div>

                <!-- Recommendations Tab -->
                <div v-if="activeTab === 'recommendations'" class="recommendations-section">
                  <div class="section-header">
                    <button class="regen-btn"
                            :disabled="recommendationsLoading"
                            @click="generateRecommendations">
                      {{ hasRecommendations ? 'Regenerate' : 'Generate' }}
                    </button>
                  </div>
                  <div v-if="recommendationsLoading" class="loading">Loading…</div>
                  <div v-else-if="recommendations.length" class="recommendations-content">
                    <PaperCard 
                      v-for="paper in recommendations" 
                      :key="`${paper.paper_id}-${paper.platform || 'arxiv'}`" 
                      :paper="paper" 
                    />
                  </div>
                  <div v-else class="no-content">No recommendations yet.</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 侧栏：仅评论区域 -->
          <div class="comment-area" :class="{ 'collapsed': isCommentCollapsed }">
            <!-- 左侧拖拽手柄 -->
            <div 
              class="comment-resize-handle"
              @mousedown="startCommentResize"
              title="Drag to resize comments area"
            ></div>
            <div class="comment-header" v-show="!isCommentCollapsed">
              <h3>Comments</h3>
            </div>
            <div class="comment-content-wrapper" v-show="!isCommentCollapsed">
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
        </div>
      </template>
      <div v-else class="empty-placeholder">
        Select a folder to view its papers.
      </div>
    </div>


<transition-group name="modal-float">
  <div
    v-for="m in openModals"
    :key="m.paper.paper_id"
    class="floating-modal compact-modal"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="'modal-title-' + m.paper.paper_id"
    tabindex="-1"
    :style="styleFrom(m)"
    @mousedown="bringToFront(m)"
  >
    <header
      class="modal-header compact-header"
      @mousedown="onModalDragStart($event, m)"
    >
      <a
        :href="m.paper.pdf_url"
        target="_blank"
        :id="'modal-title-' + m.paper.paper_id"
        class="modal-title-link"
        title="Open PDF"
      >{{ m.paper.title }}</a>
      <button class="close-btn" @click="closeModal(m.paper.paper_id)" aria-label="Close">✖</button>
    </header>

    <section class="modal-body compact-body" :id="'modal-desc-' + m.paper.paper_id">
      <p><strong>Authors:</strong> {{ m.paper.authors.join(', ') }}</p>
      <p><strong>Published:</strong> {{ formatDate(m.paper.published_date) }}</p>
      <p>
        <strong>Abstract: </strong>
        <span v-if="!m.abstractExpanded">
          {{ m.paper.abstract.length > 220 ? m.paper.abstract.slice(0, 220) + '...' : m.paper.abstract }}
          <a v-if="m.paper.abstract.length > 220" class="expand-link" @click="m.abstractExpanded = true">Expand</a>
        </span>
        <span v-else>
          {{ m.paper.abstract }}
          <a class="expand-link" @click="m.abstractExpanded = false">Collapse</a>
        </span>
      </p>

      <!-- 每个弹窗自己的评论区 -->
      <div class="paper-comments">
        <h4 class="pc-title">Comments</h4>
        <ul class="paper-comment-list">
          <li v-for="c in m.comments" :key="c.id" class="pc-item">
            <div class="pc-meta">
              <span class="pc-author">{{ c.commenter_name || 'Anonymous' }}</span>
              <span class="pc-dot">·</span>
              <span class="pc-date">{{ formatDate(c.created_at) }}</span>
              <button
                v-if="c.commenter_id === userId"
                class="delete-btn"
                title="Delete"
                @click="deletePaperCommentFor(m, c.id)"
              >✖</button>
            </div>
            <div class="pc-content">{{ c.content }}</div>
          </li>
          <li v-if="!m.comments.length" class="pc-empty">No comments yet.</li>
        </ul>
        <div class="paper-comment-input">
          <textarea
            v-model="m.newComment"
            class="pc-textarea"
            placeholder="Leave a comment…"
            rows="2"
          ></textarea>
          <button
            class="pc-submit"
            :disabled="!m.newComment.trim() || m.submitting"
            @click="submitPaperCommentFor(m)"
          >
            {{ m.submitting ? 'Submitting…' : 'Submit' }}
          </button>
        </div>
      </div>
    </section>

    <!-- 8 个缩放句柄（传入当前 modal m） -->
    <div class="resize-handle handle-n"  @mousedown.stop="onModalResizeStart($event, m, 'n')"  />
    <div class="resize-handle handle-s"  @mousedown.stop="onModalResizeStart($event, m, 's')"  />
    <div class="resize-handle handle-e"  @mousedown.stop="onModalResizeStart($event, m, 'e')"  />
    <div class="resize-handle handle-w"  @mousedown.stop="onModalResizeStart($event, m, 'w')"  />
    <div class="resize-handle handle-ne" @mousedown.stop="onModalResizeStart($event, m, 'ne')" />
    <div class="resize-handle handle-nw" @mousedown.stop="onModalResizeStart($event, m, 'nw')" />
    <div class="resize-handle handle-se" @mousedown.stop="onModalResizeStart($event, m, 'se')" />
    <div class="resize-handle handle-sw" @mousedown.stop="onModalResizeStart($event, m, 'sw')" />
  </div>
</transition-group>

  </div>

</template>



<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount,computed,reactive, nextTick } from 'vue'
import SharedSidebar   from '@/components/SharedSidebar.vue'
import GraphWithDetail from '@/components/GraphWithDetail.vue'
import SharedGraph3D   from '@/components/SharedGraph3D.vue'
import PaperCard       from '@/components/PaperCard.vue'
import api             from '@/services/api'
import MarkdownIt from 'markdown-it'
import type { Paper as ApiPaper } from '@/types/paper'
const md = new MarkdownIt({ linkify: true, breaks: true })
const papersMap = reactive<Record<number, LocalPaper[]>>({})
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const props = defineProps<{ folderId: number | null }>()

// 本地Paper类型（用于图表显示）
interface LocalPaper {
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
  platform?: string
  embedding?: number[]
}

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
const activeDrag = ref<{ m: ModalState; dx: number; dy: number } | null>(null)
const activeResize = ref<{
  m: ModalState; dir: Dir;
  startX: number; startY: number;
  startW: number; startH: number;
  startL: number; startT: number;
} | null>(null)

function clampModal(m: ModalState) {
  const margin = 8
  const maxLeft = Math.max(margin, window.innerWidth  - m.width  - margin)
  const maxTop  = Math.max(margin, window.innerHeight - m.height - margin)
  m.left = Math.min(Math.max(m.left, margin), maxLeft)
  m.top  = Math.min(Math.max(m.top,  margin), maxTop)
}

function onModalDragStart(e: MouseEvent, m: ModalState) {
  // 避免拖拽 close 按钮/链接
  const target = e.target as HTMLElement
  if (target.closest('.close-btn') || target.closest('a')) return
  bringToFront(m)
  activeDrag.value = { m, dx: e.clientX - m.left, dy: e.clientY - m.top }
}

function onModalResizeStart(e: MouseEvent, m: ModalState, dir: Dir) {
  bringToFront(m)
  activeResize.value = {
    m, dir,
    startX: e.clientX, startY: e.clientY,
    startW: m.width, startH: m.height,
    startL: m.left,  startT: m.top
  }
}

function onWindowMouseMove(e: MouseEvent) {
  if (activeDrag.value) {
    const { m, dx, dy } = activeDrag.value
    m.left = e.clientX - dx
    m.top  = e.clientY - dy
    clampModal(m)
  } else if (activeResize.value) {
    const { m, dir, startX, startY, startW, startH, startL, startT } = activeResize.value
    const dx = e.clientX - startX
    const dy = e.clientY - startY

    let newLeft = startL
    let newTop  = startT
    let newW    = startW
    let newH    = startH

    if (dir.includes('e')) newW = startW + dx
    if (dir.includes('s')) newH = startH + dy
    if (dir.includes('w')) { newW = startW - dx; newLeft = startL + dx }
    if (dir.includes('n')) { newH = startH - dy; newTop  = startT + dy }

    const minW = 360, minH = 220
    if (newW < minW) { if (dir.includes('w')) newLeft -= (minW - newW); newW = minW }
    if (newH < minH) { if (dir.includes('n')) newTop  -= (minH - newH); newH = minH }

    const margin = 8
    const maxRight  = window.innerWidth  - margin
    const maxBottom = window.innerHeight - margin

    if (newLeft < margin) {
      const overflow = margin - newLeft
      newLeft = margin
      if (dir.includes('w')) newW = Math.max(minW, newW - overflow)
    }
    if (newTop < margin) {
      const overflow = margin - newTop
      newTop = margin
      if (dir.includes('n')) newH = Math.max(minH, newH - overflow)
    }
    if (newLeft + newW > maxRight) {
      const overflow = newLeft + newW - maxRight
      if (dir.includes('e')) newW = Math.max(minW, newW - overflow)
      else newLeft = maxRight - newW
    }
    if (newTop + newH > maxBottom) {
      const overflow = newTop + newH - maxBottom
      if (dir.includes('s')) newH = Math.max(minH, newH - overflow)
      else newTop = maxBottom - newH
    }

    m.left = newLeft
    m.top  = newTop
    m.width  = newW
    m.height = newH
  }
}

function onWindowMouseUp() {
  activeDrag.value = null
  activeResize.value = null
}

function closeTopMost() {
  if (!openModals.value.length) return
  const m = openModals.value.reduce((a, b) => (a.z > b.z ? a : b))
  closeModal(m.paper.paper_id)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') closeTopMost()
}

onMounted(() => {
  window.addEventListener('mousemove', onWindowMouseMove)
  window.addEventListener('mouseup', onWindowMouseUp)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onWindowMouseMove)
  window.removeEventListener('mouseup', onWindowMouseUp)
  window.removeEventListener('keydown', onKeydown)
  
  // 清理拖拽相关事件
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
  
  // 清理评论区拖拽事件
  document.removeEventListener('mousemove', handleCommentResize)
  document.removeEventListener('mouseup', stopCommentResize)
  
  // 清理侧边栏拖拽事件
  document.removeEventListener('mousemove', handleSidebarResize)
  document.removeEventListener('mouseup', stopSidebarResize)
})

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
  platform?: string
  embedding?: number[]  // 可选的向量表示

}
type Dir = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw'

interface ModalState {
  paper: LocalPaper
  top: number
  left: number
  width: number
  height: number
  z: number
  abstractExpanded: boolean
  comments: Array<{ id:number; content:string; commenter_name:string; commenter_id:string; created_at:string }>
  newComment: string
  submitting: boolean
}

const openModals = ref<ModalState[]>([])
let zSeed = 3000  // 置顶用

function styleFrom(m: ModalState) {
  return {
    top: `${m.top}px`,
    left: `${m.left}px`,
    width: `${m.width}px`,
    height: `${m.height}px`,
    right: 'auto',
    bottom: 'auto',
    maxHeight: 'none',
    zIndex: m.z
  }
}

function findModalIndex(paperId: string) {
  return openModals.value.findIndex(x => x.paper.paper_id === paperId)
}

function bringToFront(m: ModalState) {
  m.z = ++zSeed
}

function cascadePosition(w: number, h: number, idx: number) {
  const offset = idx * 28
  const left = Math.max(8, window.innerWidth  - w - 180 - offset)
  const top  = Math.max(8, window.innerHeight - h -  36 - offset)
  return { left, top }
}

async function openDetailModal(p: LocalPaper) {
  // 已打开则置顶
  const i = findModalIndex(p.paper_id)
  if (i >= 0) { bringToFront(openModals.value[i]); return }

  const width = 540, height = 360
  const { left, top } = cascadePosition(width, height, openModals.value.length)

  const m: ModalState = {
    paper: p,
    top, left, width, height,
    z: ++zSeed,
    abstractExpanded: false,
    comments: [],
    newComment: '',
    submitting: false
  }
  openModals.value.push(m)
  await loadPaperCommentsInto(m)
}



// 处理图表节点点击
function handleNodeClick(paper: LocalPaper | null) {
  if (paper) {
    openDetailModal(paper)
  }
}

function closeModal(paperId: string) {
  const i = findModalIndex(paperId)
  if (i >= 0) openModals.value.splice(i, 1)
}

async function loadPaperCommentsInto(m: ModalState) {
  try {
    m.comments = await api.get_paper_comments(m.paper.paper_id) || []
  } catch (e) {
    console.error('Failed to load paper comments', e)
    m.comments = []
  }
}

async function submitPaperCommentFor(m: ModalState) {
  if (!m.newComment.trim()) return
  m.submitting = true
  try {
    const saved = await api.add_paper_comment(m.paper.paper_id, m.newComment.trim())
    m.comments.push(saved)
    m.newComment = ''
  } catch (e) {
    alert('Failed to add comment.')
  } finally {
    m.submitting = false
  }
}

async function deletePaperCommentFor(m: ModalState, cid: number) {
  if (!confirm('Delete this comment?')) return
  try {
    await api.delete_paper_comment(cid)
    m.comments = m.comments.filter(c => c.id !== cid)
  } catch (e) {
    alert('Failed to delete comment.')
  }
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
const graphData = ref<LocalPaper[]>([])
const selected = ref<LocalPaper|null>(null)
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
const abstractExpanded = ref(false)

/* ---------- 推荐功能 state ---------- */
const activeTab = ref<'summary' | 'recommendations'>('summary')
const recommendationsMap = reactive<Record<number, ApiPaper[]>>({}) // 每个文件夹的推荐缓存
const recommendationsLoading = ref(false)

// 当前文件夹的推荐内容（计算属性）
const recommendations = computed(() => {
  return activeId.value ? (recommendationsMap[activeId.value] || []) : []
})

// 检查当前文件夹是否有推荐内容
const hasRecommendations = computed(() => {
  return activeId.value && recommendationsMap[activeId.value] && recommendationsMap[activeId.value].length > 0
})

/* ---------- 侧边栏拖拽调整功能 ---------- */
const sidebarWidth = ref(260) // 初始宽度
const isSidebarResizing = ref(false)
const sidebarResizeStartX = ref(0)
const sidebarResizeStartWidth = ref(0)
const isSidebarCollapsed = ref(false) // 跟踪侧边栏折叠状态

// 计算侧边栏容器宽度
const sidebarContainerWidth = computed(() => {
  return isSidebarCollapsed.value ? '60px' : sidebarWidth.value + 'px'
})

/* ---------- 评论区拖拽调整功能 ---------- */
const commentAreaWidth = ref(300) // 初始宽度
const isCommentResizing = ref(false)
const commentResizeStartX = ref(0)
const commentResizeStartWidth = ref(0)

// 计算属性：判断评论区是否应该完全折叠
const isCommentCollapsed = computed(() => commentAreaWidth.value <= 20)

function startCommentResize(event: MouseEvent) {
  isCommentResizing.value = true
  commentResizeStartX.value = event.clientX
  commentResizeStartWidth.value = commentAreaWidth.value
  
  // 禁用过渡效果，避免拖拽延迟
  const contentWrap = document.querySelector('.content-wrap') as HTMLElement
  if (contentWrap) {
    contentWrap.style.transition = 'none'
  }
  
  document.addEventListener('mousemove', handleCommentResize)
  document.addEventListener('mouseup', stopCommentResize)
  document.body.style.cursor = 'ew-resize'
  
  event.preventDefault()
}

function handleCommentResize(event: MouseEvent) {
  if (!isCommentResizing.value) return
  
  // 使用 requestAnimationFrame 确保平滑更新
  requestAnimationFrame(() => {
    const deltaX = commentResizeStartX.value - event.clientX // 向左拖拽为正值
    const newWidth = commentResizeStartWidth.value + deltaX
    
      // 设置最小和最大宽度限制
  const minWidth = 8 // 最小宽度改为只显示拖拽线
  const maxWidth = window.innerWidth * 0.5 // 最大宽度为屏幕宽度的50%
    
    commentAreaWidth.value = Math.max(minWidth, Math.min(maxWidth, newWidth))
  })
}

function stopCommentResize() {
  isCommentResizing.value = false
  document.removeEventListener('mousemove', handleCommentResize)
  document.removeEventListener('mouseup', stopCommentResize)
  document.body.style.cursor = ''
  
  // 恢复过渡效果
  const contentWrap = document.querySelector('.content-wrap') as HTMLElement
  if (contentWrap) {
    contentWrap.style.transition = 'grid-template-columns 0.3s ease'
  }
}

function startSidebarResize(event: MouseEvent) {
  isSidebarResizing.value = true
  sidebarResizeStartX.value = event.clientX
  sidebarResizeStartWidth.value = sidebarWidth.value
  
  // 禁用过渡效果，避免拖拽延迟
  const sidebarContainer = document.querySelector('.sidebar-container') as HTMLElement
  const sharedSidebar = document.querySelector('.shared-sidebar') as HTMLElement
  
  if (sidebarContainer) {
    sidebarContainer.style.transition = 'none'
  }
  if (sharedSidebar) {
    sharedSidebar.style.transition = 'none'
  }
  
  document.addEventListener('mousemove', handleSidebarResize)
  document.addEventListener('mouseup', stopSidebarResize)
  document.body.style.cursor = 'ew-resize'
  
  event.preventDefault()
}

function handleSidebarResize(event: MouseEvent) {
  if (!isSidebarResizing.value) return
  
  // 使用 requestAnimationFrame 确保平滑更新
  requestAnimationFrame(() => {
    const deltaX = event.clientX - sidebarResizeStartX.value // 向右拖拽为正值
    const newWidth = sidebarResizeStartWidth.value + deltaX
    
    // 设置最小和最大宽度限制
    const minWidth = 200 // 最小宽度
    const maxWidth = window.innerWidth * 0.4 // 最大宽度为屏幕宽度的40%
    
    sidebarWidth.value = Math.max(minWidth, Math.min(maxWidth, newWidth))
  })
}

function stopSidebarResize() {
  isSidebarResizing.value = false
  document.removeEventListener('mousemove', handleSidebarResize)
  document.removeEventListener('mouseup', stopSidebarResize)
  document.body.style.cursor = ''
  
  // 恢复过渡效果
  const sidebarContainer = document.querySelector('.sidebar-container') as HTMLElement
  const sharedSidebar = document.querySelector('.shared-sidebar') as HTMLElement
  
  if (sidebarContainer) {
    sidebarContainer.style.transition = 'flex 0.3s ease'
  }
  if (sharedSidebar) {
    sharedSidebar.style.transition = 'all 0.3s ease'
  }
}

/* ---------- 底部区域拖拽调整功能 ---------- */
const bottomAreaHeight = ref(320) // 初始高度
const isResizing = ref(false)
const initialMouseY = ref(0)
const initialHeight = ref(0)

function startResize(event: MouseEvent) {
  isResizing.value = true
  initialMouseY.value = event.clientY
  initialHeight.value = bottomAreaHeight.value
  
  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'ns-resize'
  
  // 防止文本选择
  event.preventDefault()
}

function handleResize(event: MouseEvent) {
  if (!isResizing.value) return
  
  const deltaY = initialMouseY.value - event.clientY // 向上拖拽为正值
  const newHeight = initialHeight.value + deltaY
  
  // 设置最小和最大高度限制
  const minHeight = 80 // 降低最小高度，只保留标签页导航的空间
  const maxHeight = window.innerHeight * 0.8 // 增加最大高度到80%
  
  bottomAreaHeight.value = Math.max(minHeight, Math.min(maxHeight, newHeight))
}

function stopResize() {
  isResizing.value = false
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
}

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

/* ---------- 推荐功能 API ---------- */
async function generateRecommendations() {
  if (!activeId.value) return
  recommendationsLoading.value = true
  try {
    const result = await api.getFolderRecommendations(activeId.value, {
      limit: 20,
      exclude_existing: true
    })
    // 将推荐结果存储到对应文件夹的缓存中
    recommendationsMap[activeId.value] = result || []
  } catch (error) {
    console.error('Failed to generate recommendations:', error)
    alert('Failed to generate recommendations')
  } finally {
    recommendationsLoading.value = false
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
    
    // 清理对应的推荐缓存
    if (recommendationsMap[folderId]) {
      delete recommendationsMap[folderId]
    }
    
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

  /* ③ 重置推荐loading状态（当切换文件夹时） */
  recommendationsLoading.value = false

  /* ③ 计算余弦 → citeMap → graphData （原来 watch 里的代码整段搬过来） */
  const citeMap = new Map<string, string[]>();
  const edges: {u:string, v:string, w:number}[] = [];

  const cosine = (a:number[], b:number[])=>{
    let dot=0,na=0,nb=0;
    for(let i=0;i<a.length;i++){
      dot+=a[i]*b[i]; na+=a[i]*a[i]; nb+=b[i]*b[i];
    }
    return dot/(Math.sqrt(na)*Math.sqrt(nb)+1e-10);
  }

  for(let i=0;i<files.length;i++){
    const fi=files[i]; if(!fi.embedding) continue;
    for(let j=i+1;j<files.length;j++){
      const fj=files[j]; if(!fj.embedding) continue;
      const sim = cosine(fi.embedding,fj.embedding);
      if(sim > .96){
        edges.push({u:fi.paper_id, v:fj.paper_id, w:sim});
      }
    }
  }

  // 排序并截断
  const n = files.length;
  if(edges.length > 2*n){
    edges.sort((a,b)=>b.w-a.w);
    edges.length = 2*n;
  }

  // 重建 citeMap
  for(const {u,v} of edges){
    (citeMap.get(u)??citeMap.set(u,[]).get(u)!).push(v);
    (citeMap.get(v)??citeMap.set(v,[]).get(v)!).push(u);
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
           if (n?.paper) openDetailModal(n.paper)
    })
  }
})

// 关闭弹窗
function closeDetail() {
  detailPaper.value = null
}


// --- 生命周期钩子 ---
onMounted(async () => {
  window.addEventListener('popstate', onPopState)
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



watch(detailPaper, async (val) => {
  if (val) {
    abstractExpanded.value = false
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

/* ---------- 新增：拖拽与缩放状态 ====== */
const modalTop   = ref(100)
const modalLeft  = ref(100)
const modalWidth = ref(540)
const modalHeight= ref(360)

const dragging = ref(false)
const dragOffset = { x: 0, y: 0 }


const resizing = ref(false)
const resizeDir = ref<Dir | null>(null)
const resizeStart = { x: 0, y: 0, w: 0, h: 0, l: 0, t: 0 }

const modalStyle = computed(() => ({
  top: `${modalTop.value}px`,
  left: `${modalLeft.value}px`,
  width: `${modalWidth.value}px`,
  height: `${modalHeight.value}px`,
  right: 'auto',
  bottom: 'auto',
  maxHeight: 'none'
}))

function clampPosition() {
  const maxLeft = Math.max(0, window.innerWidth  - modalWidth.value  - 8)
  const maxTop  = Math.max(0, window.innerHeight - modalHeight.value - 8)
  modalLeft.value = Math.max(8, Math.min(modalLeft.value, maxLeft))
  modalTop.value  = Math.max(8, Math.min(modalTop.value,  maxTop))
}

function onDragStart(e: MouseEvent) {
  // 避免拖拽 close 按钮/链接
  const target = e.target as HTMLElement
  if (target.closest('.close-btn') || target.closest('a')) return
  dragging.value = true
  dragOffset.x = e.clientX - modalLeft.value
  dragOffset.y = e.clientY - modalTop.value
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e: MouseEvent) {
  if (!dragging.value) return
  modalLeft.value = e.clientX - dragOffset.x
  modalTop.value  = e.clientY - dragOffset.y
  clampPosition()
}

function onDragEnd() {
  dragging.value = false
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
}

function onResizeStart(e: MouseEvent, dir: Dir) {
  resizing.value = true
  resizeDir.value = dir
  resizeStart.x = e.clientX
  resizeStart.y = e.clientY
  resizeStart.w = modalWidth.value
  resizeStart.h = modalHeight.value
  resizeStart.l = modalLeft.value
  resizeStart.t = modalTop.value
  window.addEventListener('mousemove', onResizeMove)
  window.addEventListener('mouseup', onResizeEnd)
}

function onResizeMove(e: MouseEvent) {
  if (!resizing.value || !resizeDir.value) return
  const dx = e.clientX - resizeStart.x
  const dy = e.clientY - resizeStart.y

  let newLeft = resizeStart.l
  let newTop  = resizeStart.t
  let newW    = resizeStart.w
  let newH    = resizeStart.h

  const dir = resizeDir.value

  // 基础计算：按方向增减尺寸与位置
  if (dir.includes('e')) newW = resizeStart.w + dx
  if (dir.includes('s')) newH = resizeStart.h + dy
  if (dir.includes('w')) {
    newW = resizeStart.w - dx
    newLeft = resizeStart.l + dx
  }
  if (dir.includes('n')) {
    newH = resizeStart.h - dy
    newTop = resizeStart.t + dy
  }

  // 最小尺寸
  const minW = 360, minH = 220
  if (newW < minW) {
    if (dir.includes('w')) newLeft -= (minW - newW)
    newW = minW
  }
  if (newH < minH) {
    if (dir.includes('n')) newTop -= (minH - newH)
    newH = minH
  }

  // 视口边界
  const margin = 8
  const maxRight = window.innerWidth  - margin
  const maxBottom= window.innerHeight - margin

  // 左边界
  if (newLeft < margin) {
    const overflow = margin - newLeft
    newLeft = margin
    if (dir.includes('w')) newW = Math.max(minW, newW - overflow)
  }
  // 顶边界
  if (newTop < margin) {
    const overflow = margin - newTop
    newTop = margin
    if (dir.includes('n')) newH = Math.max(minH, newH - overflow)
  }
  // 右边界
  if (newLeft + newW > maxRight) {
    const overflow = newLeft + newW - maxRight
    if (dir.includes('e')) {
      newW = Math.max(minW, newW - overflow)
    } else {
      newLeft = maxRight - newW
    }
  }
  // 底边界
  if (newTop + newH > maxBottom) {
    const overflow = newTop + newH - maxBottom
    if (dir.includes('s')) {
      newH = Math.max(minH, newH - overflow)
    } else {
      newTop = maxBottom - newH
    }
  }

  modalLeft.value  = newLeft
  modalTop.value   = newTop
  modalWidth.value = newW
  modalHeight.value= newH
}

function onResizeEnd() {
  resizing.value = false
  resizeDir.value = null
  window.removeEventListener('mousemove', onResizeMove)
  window.removeEventListener('mouseup', onResizeEnd)
}

// 打开时设置初始位置与尺寸
watch(detailPaper, async (p) => {
  if (p) {
    // ...existing code...
    // 计算初始位置：右下
    modalWidth.value  = 540
    modalHeight.value = 360
    modalLeft.value   = Math.max(8, window.innerWidth  - modalWidth.value  - 180)
    modalTop.value    = Math.max(8, window.innerHeight - modalHeight.value - 36)
    clampPosition()
  } else {
    // ...existing code...
  }
})

// 清理
onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
  window.removeEventListener('mousemove', onResizeMove)
  window.removeEventListener('mouseup', onResizeEnd)
})


/* ---------- 新增：Paper 评论状态 ---------- */
const paperComments = ref<Array<{ id:number; content:string; commenter_name:string; commenter_id:string; created_at:string }>>([])
const newPaperComment = ref('')
const submittingPaperComment = ref(false)

/* ---------- 新增：加载指定论文的评论 ---------- */
async function loadPaperComments(paperId: string) {
  try {
    paperComments.value = await api.get_paper_comments(paperId) || []
  } catch (e) {
    console.error('Failed to load paper comments', e)
    paperComments.value = []
  }
}

/* ---------- 新增：提交论文评论 ---------- */
async function submitPaperComment() {
  if (!detailPaper.value || !newPaperComment.value.trim()) return
  submittingPaperComment.value = true
  try {
    const saved = await api.add_paper_comment(detailPaper.value.paper_id, newPaperComment.value.trim())
    paperComments.value.push(saved)
    newPaperComment.value = ''
  } catch (e) {
    alert('Failed to add comment.')
  } finally {
    submittingPaperComment.value = false
  }
}

/* ---------- 新增：删除论文评论 ---------- */
async function deletePaperComment(cid: number) {
  if (!confirm('Delete this comment?')) return
  try {
    await api.delete_paper_comment(cid)
    paperComments.value = paperComments.value.filter(c => c.id !== cid)
  } catch (e) {
    alert('Failed to delete comment.')
  }
}

// 监听弹窗打开/切换论文时加载评论并重置展开状态
watch(detailPaper, async (p) => {
  if (p) {
    abstractExpanded.value = false
    await loadPaperComments(p.paper_id)
    await nextTick()
    ;(modalContent.value as HTMLElement | null)?.focus()
  } else {
    paperComments.value = []
    newPaperComment.value = ''
  }
})
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

.loading, .no-content {
  color: #6b7280;
  font-size: 0.9rem;
  padding: 2rem;
  text-align: center;
}

.summary-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.recommendations-content {
  flex: 1 1 auto;
  overflow-y: auto; /* vertical scroll when overflow */
  overflow-x: hidden;
  padding: 1rem;
  display: block; /* normal block is fine; no !important */
  gap: 0.75rem;
  min-height: 0; /* allow shrinking within flex container */
}

/* 推荐区域的PaperCard样式覆盖 */
.recommendations-content :deep(.paper-card) {
  padding: 0.75rem !important;
  min-height: auto !important;
  height: auto !important; /* 覆盖固定高度 */
  margin-bottom: 0.75rem !important; /* 为block布局添加间距 */
  display: block !important;
  width: 100% !important;
  box-sizing: border-box !important;
}

.recommendations-content :deep(.paper-card):last-child {
  margin-bottom: 0 !important;
}

.recommendations-content :deep(.paper-title) {
  font-size: 0.95rem !important;
  line-height: 1.3 !important;
  margin-bottom: 0.5rem !important;
}

.recommendations-content :deep(.paper-authors) {
  font-size: 0.85rem !important;
  margin-bottom: 0.25rem !important;
}

.recommendations-content :deep(.paper-meta) {
  font-size: 0.8rem !important;
}

.recommendations-content :deep(.paper-abstract) {
  font-size: 0.85rem !important;
  line-height: 1.4 !important;
  max-height: 3.5em !important;
  overflow: hidden !important;
}

/* 自定义滚动条样式 */
.recommendations-content::-webkit-scrollbar {
  width: 6px;
}

.recommendations-content::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.recommendations-content::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.recommendations-content::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* 评论区域：单列 */
.comment-area {
  border-left: 1px solid #e5e7eb;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  background: #f9fafb;
  overflow: hidden;
  min-height: 0;
  position: relative;
  transition: padding 0.3s ease;
}

/* 当评论区完全折叠时，只显示拖拽线 */
.comment-area.collapsed {
  padding: 0;
  background: transparent;
  border-left: none;
}

/* 评论区拖拽手柄 */
.comment-resize-handle {
  position: absolute;
  left: -4px;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: ew-resize;
  background: transparent;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
}

.comment-resize-handle:hover {
  background: rgba(59, 130, 246, 0.1);
}

.comment-resize-handle::before {
  content: '';
  width: 4px;
  height: 40px;
  background: #cbd5e1;
  border-radius: 2px;
  transition: background-color 0.2s;
}

.comment-resize-handle:hover::before {
  background: #3b82f6;
}

/* 折叠状态下的拖拽手柄样式 */
.comment-area.collapsed .comment-resize-handle {
  left: 0;
  width: 100%;
  background: rgba(59, 130, 246, 0.05);
}

.comment-area.collapsed .comment-resize-handle::before {
  background: #3b82f6;
  width: 2px;
  height: 60px;
}

.comment-area.collapsed .comment-resize-handle:hover {
  background: rgba(59, 130, 246, 0.1);
}

.comment-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  flex-shrink: 0;
}

.comment-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #374151;
}



.comment-content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
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

/* 左侧容器：包含 Sidebar 和拖拽手柄 */
.sidebar-container {
  flex: 0 0 v-bind(sidebarContainerWidth);
  display: flex;
  position: relative;
  border-right: 1px solid #e5e7eb;
  transition: flex 0.3s ease;
  max-width: v-bind(sidebarContainerWidth); /* 强制最大宽度 */
  min-width: v-bind(sidebarContainerWidth); /* 强制最小宽度 */
  overflow: hidden; /* 防止内容溢出影响布局 */
}

/* SharedSidebar 组件：填满容器减去手柄宽度 */
.sidebar-container :deep(.shared-sidebar) {
  flex: 1;
  width: 100%;
  border-right: none;
  overflow-y: auto;
  overflow-x: hidden; /* 防止水平滚动 */
  min-width: 0; /* 允许收缩 */
}

/* 侧边栏拖拽手柄 */
.sidebar-resize-handle {
  position: absolute;
  right: -4px;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: ew-resize;
  background: transparent;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-resize-handle:hover {
  background: rgba(59, 130, 246, 0.1);
}

.sidebar-resize-handle::before {
  content: '';
  width: 4px;
  height: 40px;
  background: #cbd5e1;
  border-radius: 2px;
  transition: background-color 0.2s;
}

.sidebar-resize-handle:hover::before {
  background: #3b82f6;
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

/* 底部区域：可拖拽调整高度 */
.bottom-area {
  flex: 0 0 auto; /* 改为auto，使用动态高度 */
  border-top: 1px solid #e5e7eb;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  position: relative;
  min-height: 80px; /* 降低最小高度，只保留标签页导航的空间 */
  max-height: 80vh; /* 增加最大高度到80% */
}

/* 水平拖拽手柄 */
.resize-handle-horizontal {
  position: absolute;
  top: -4px;
  left: 0;
  right: 0;
  height: 8px;
  cursor: ns-resize;
  background: transparent;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
}

.resize-handle-horizontal:hover {
  background: rgba(59, 130, 246, 0.1);
}

.resize-handle-horizontal::before {
  content: '';
  width: 40px;
  height: 4px;
  background: #cbd5e1;
  border-radius: 2px;
  transition: background-color 0.2s;
}

.resize-handle-horizontal:hover::before {
  background: #3b82f6;
}

/* 标签页导航 */
.tab-nav {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
}

.tab-btn {
  flex: 1;
  padding: 0.75rem 1rem;
  border: none;
  background: transparent;
  cursor: pointer;
  font-weight: 500;
  color: #6b7280;
  transition: all 0.2s;
  border-bottom: 2px solid transparent;
}

.tab-btn:hover {
  background: #f9fafb;
  color: #374151;
}

.tab-btn.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  background: #fff;
}

/* 标签页内容 */
.tab-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 允许收缩 */
  height: 100%; /* 明确的高度 */
}

.summary-section,
.recommendations-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0; /* 确保子元素可以正确收缩 */
  height: 100%; /* 明确的高度 */
}

.section-header {
  padding: 1rem;
  background: #f8fafc;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
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
/* 把内容两栏改成网格：左自适应，右可调宽度 */
.content-wrap{
  display: grid;
  grid-template-columns: 1fr v-bind(commentAreaWidth + 'px');  /* 使用响应式宽度 */
  width: 100%;
  min-width: 0;   /* 关键：允许整体收缩 */
  min-height: 0;  /* 允许子元素再收缩 */
  transition: grid-template-columns 0.3s ease;
}

/* 主列、评论列都要能收缩或固定 */
.main-column { min-width: 0; overflow: hidden; }
.comment-area{
  min-width: 0;          /* grid 已固定宽，再加一次保险 */
  overflow-y: auto;      /* 纵向滚动 */
}

/* 紧凑版弹窗 */
.compact-modal {
  width: auto;
  max-width: 98vw;
  padding: 0;
  border-radius: 12px;
  font-size: 0.92rem;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  background: #fff;
}
.compact-header {
  padding: .8rem 1.5rem .7rem 1.5rem !important;
  border-bottom: 1px solid #e5e7eb;
  background: #f8fafc;
  border-radius: 12px 12px 0 0;
  display: flex;
  align-items: center;
}
.modal-title-link {
  font-size: 1.08rem;
  font-weight: 600;
  color: #2563eb;
  text-decoration: underline;
  flex: 1;
  margin-right: .5rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color .18s;
}
.modal-title-link:hover {
  color: #1e40af;
}
.compact-body {
  padding: 1rem 1.5rem 1.2rem 1.5rem !important;
  font-size: 0.93rem;
  color: #374151;
  display: flex;
  flex-direction: column;
  gap: .25em;
  flex: 1 1 auto;
  overflow-y: auto;
  max-height: none; /* 覆盖原有 320px 限制，随外层高度伸缩 */
}
.compact-body p {
  margin: 0 0 .18em 0;
  font-size: .93em;
  line-height: 1.45;
  letter-spacing: 0.01em;
  word-break: break-word;
}
.expand-link {
  color: #2563eb;
  cursor: pointer;
  margin-left: .5em;
  font-size: .93em;
  text-decoration: underline;
  user-select: none;
}
.expand-link:hover {
  color: #1e40af;
  text-decoration: underline;
}

/* 悬浮窗样式 */
.floating-modal {
  position: fixed;
  z-index: 2000;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  border-radius: 12px;
  background: #fff;
  animation: floatIn .22s;
  min-height: 260px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
@media (max-width: 800px) {
  .floating-modal {
    right: 8px;
    left: 8px;
    width: auto !important;
    max-width: 98vw !important;
  }
}

/* 悬浮窗动画 */
.modal-float-enter-active, .modal-float-leave-active {
  transition: opacity .22s;
}
.modal-float-enter-from, .modal-float-leave-to {
  opacity: 0;
}

/* ★ Paper 评论区样式 */
.paper-comments {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #e5e7eb;
}
.pc-title {
  margin: 0 0 .5rem 0;
  font-size: .95rem;
  font-weight: 600;
  color: #334155;
}
.paper-comment-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: .5rem;
  max-height: 180px;       /* 让评论区域可滚动 */
  overflow-y: auto;
}
.pc-item {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: .5rem .6rem;
}
.pc-meta {
  font-size: .78rem;
  color: #6b7280;
  display: flex;
  align-items: center;
  gap: .35rem;
  margin-bottom: .15rem;
}
.pc-author { font-weight: 600; color: #374151; }
.pc-dot { color: #9ca3af; }
.pc-content { font-size: .9rem; color: #374151; white-space: pre-wrap; word-break: break-word; }
.pc-empty { color: #9ca3af; text-align: center; }

.paper-comment-input {
  display: flex;
  gap: .5rem;
  align-items: flex-start;
  margin-top: .6rem;
}
.pc-textarea {
  flex: 1;
  min-height: 54px;
  padding: .45rem .6rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: .9rem;
  resize: vertical;
}
.pc-submit {
  flex: 0 0 auto;
  padding: .45rem .9rem;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: .88rem;
  cursor: pointer;
}
.pc-submit:disabled { opacity: .6; cursor: not-allowed; }

/* 让 header 表示可拖拽 */
.modal-header.compact-header {
  cursor: move;
  user-select: none;
}

/* 通用句柄基类 */
.resize-handle { position: absolute; z-index: 1; }

/* 边句柄：更容易抓取，厚度 6px */
.handle-n { top: -3px; left: 20px; right: 20px; height: 6px; cursor: n-resize; }
.handle-s { bottom: -3px; left: 20px; right: 20px; height: 6px; cursor: s-resize; }
.handle-e { right: -3px; top: 20px; bottom: 20px; width: 6px; cursor: e-resize; }
.handle-w { left: -3px; top: 20px; bottom: 20px; width: 6px; cursor: w-resize; }

/* 角句柄：12px 小方块 */
.handle-ne { right: -4px; top: -4px; width: 12px; height: 12px; cursor: ne-resize; }
.handle-nw { left:  -4px; top: -4px; width: 12px; height: 12px; cursor: nw-resize; }
.handle-se { right: -4px; bottom: -4px; width: 12px; height: 12px; cursor: se-resize; }
.handle-sw { left:  -4px; bottom: -4px; width: 12px; height: 12px; cursor: sw-resize; }

/* 可选：给角句柄一个淡淡的视觉提示（不想要可移除） */
.handle-ne, .handle-nw, .handle-se, .handle-sw {
  border: 2px solid #9ca3af22;
  background: #9ca3af22;
  border-radius: 2px;
}
</style>