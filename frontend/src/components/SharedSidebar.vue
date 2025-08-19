<template>
   <aside
  class="shared-sidebar"
  :class="{ collapsed: isCollapsed }"
  role="navigation"
  aria-label="Shared folders"
>
  <!-- ── Header ───────────────────────────── -->
  <header class="shared-sidebar__header">
    <!-- 折叠/展开按钮 -->
    <button
      class="collapse-btn"
      @click="toggleSidebar"
      :title="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
    >
      <!-- 简单汉堡图标，可换成你自己的 -->
      <svg viewBox="0 0 24 24" width="20" height="20">
        <path d="M3 6h18v2H3zm0 5h18v2H3zm0 5h18v2H3z" />
      </svg>
    </button>

    <!-- 标题只在展开时显示 -->
    <h3 v-if="!isCollapsed">Paper Folders</h3>
  </header>

  <!-- ── 列表 ─────────────────────────────── -->
  <template v-if="shares.length">
    <ul class="shared-sidebar__list">
      <li v-for="s in sortedShares" :key="s.folder_id">
        <!-- 文件夹行 -->
        <div
          class="shared-sidebar__item folder-main"
          :class="{
            'is-open': expandedId === s.folder_id,
            collapsed: isCollapsed
          }"
          @click=" toggleFolder(s.folder_id)"
          :title=" s.folder_name "
        >
          <!-- 展开箭头（收缩时隐藏） -->
          <span
            v-if="!isCollapsed"
            class="chevron"
            :class="{ open: expandedId === s.folder_id }"
          >▸</span>

          <!-- 文件夹名 & 计数（收缩时隐藏） -->
          <span v-if="!isCollapsed" class="shared-sidebar__name">
            {{ s.folder_name }}
          </span>
              <button
            v-if="!isCollapsed && s.owner_id === currentUserId"
            class="setting-btn"
            @click.stop="openSetting(s.folder_id, $event)"
            title="Folder settings"
          >⚙</button>

          <span v-if="!isCollapsed" class="shared-sidebar__count">
            {{ s.file_cnt }}
          </span>
          <span
            v-if="!isCollapsed"
            class="folder-tag"
              :class="getTagClass(s)"
  :title="getTagFull(s)"      
>
  {{ getTagShort(s) }}        
          </span>

        </div>

        <!-- 子论文列表：仅在展开且侧栏未折叠时显示 -->
        <ul
          v-if="!isCollapsed && expandedId === s.folder_id"
          class="paper-wrap"
        >
          <li
            v-if="!papersMap[s.folder_id]?.length"
            class="paper-empty"
          >Loading…</li>

          <li
            v-for="(p, idx) in papersMap[s.folder_id] || []"
            :key="p.paper_id"
            class="paper-row"
            :class="{ 'is-selected': props.activePaperId === p.paper_id }"
            @click.stop="selectPaper(p.paper_id)"
            :title="p.title"
          >
            <span class="row-no">{{ idx + 1 }}.</span>
            {{ p.title }}
          </li>
        </ul>
      </li>
    </ul>
  </template>

  <div v-else class="shared-sidebar__empty" :class="{ collapsed: isCollapsed }">
    No shared folders yet.
  </div>
</aside>



  <!-- 设置面板 Popover -->
<div v-if="panel.visible" class="setting-pop" :style="panel.style">
  <h4>Access Permission</h4>

  <label class="radio">
    <input type="radio" value="public" v-model="panel.mode"> Public
  </label>
  <label class="radio">
    <input type="radio" value="specific" v-model="panel.mode"> Specific users
  </label>

  <!-- 指定用户输入框 -->
  <div v-if="panel.mode === 'specific'" class="users-input">
  <!-- 单行输入 + Add -->
  <div class="add-user-row">
    <input v-model="panel.emailToAdd"
           placeholder="user@example.com"
           class="email-input" />
    <button class="primary small"
            :disabled="!panel.emailToAdd.trim()"
            @click="addUser">
      Add
    </button>
  </div>

<!-- 模板片段 -->
<ul class="users-list" v-if="panel.existing.length">
  <li v-for="u in panel.existing" :key="u.email" class="user-item">
    <span class="user-email">{{ u.email }}</span>

    <!-- 加上 @change -->
    <select
      v-model="u.role"
      class="role-select"
      @change="updateRole(u.email, u.role)"
    >
      <option value="viewer">Viewer</option>
      <option value="editor">Editor</option>
    </select>

    <button class="delete-user" @click="removeUser(u.email)">✖</button>
  </li>
</ul>

</div>

  <div class="btn-row">
    <button class="primary" @click="saveMode">Save</button>
    <button class="danger" @click.stop="confirmDelete">Delete folder</button>
  </div>
</div>

</template>

<script setup lang="ts">
import { reactive,ref, defineProps, defineEmits, computed } from 'vue'
import api from '../services/api'
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
  paper_id: string
  title   : string
}

const props = defineProps<{
  shares: ShareMeta[]
  papersMap: Record<number, Paper[]>
  currentUserId: string | null
  activePaperId: string | null      // ★ 新增
}>()

// emit 类型多加一个事件
const emit = defineEmits<{
  (e:'select-folder', folder_id:number): void   // ★ 新增
  (e:'load-papers', folder_id:number): void
  (e:'select', paper_id:string): void
  (e:'remove', folder_id:number): void
  (e: 'update-mode', payload: { folder_id: number; is_public: boolean }): void
}>()
const isCollapsed = ref(false)
const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

function getTagFull(s: ShareMeta) {
  if (s.owner_id === props.currentUserId) return 'OWNER'
  return s.is_public ? 'PUBLIC' : 'SHARED'
}
function getTagShort(s: ShareMeta) {
  return getTagFull(s).charAt(0)           // O / P / S
}

function getTagClass(s: ShareMeta) {
  if (s.owner_id === props.currentUserId) return 'owner'
  return s.is_public ? 'public' : 'shared'
}

function saveMode() {
  emit('update-mode', {
    folder_id: panel.fid,
    is_public: panel.mode === 'public',
  })
  panel.visible = false
}

function selectPaper(pid: string) {
  emit('select', pid)            // 告诉父组件
}


const expandedId = ref<number | null>(null)

function toggleFolder(fid: number) {
  if (expandedId.value === fid) {
    expandedId.value = null           // 收起
    return
  }

  expandedId.value = fid              // 展开
  emit('select-folder', fid)          // ★ 无论缓存与否都发

  if (!props.papersMap[fid]) {
    emit('load-papers', fid)          // 首次加载时再发
  }
}

const panel = reactive({
  visible: false,
  fid    : 0,
  mode   : 'public' as 'public' | 'specific',
  usersText: '',
  existing: [] as { email: string; role: 'viewer' | 'editor' }[],
  style  : {} as Record<string,string>,   // { left:'', top:'' }
  emailToAdd: '',
})

// 新增排序后的 shares 计算属性
const sortedShares = computed(() => {
  return [...props.shares].sort((a, b) => {
    // 1. owner（自己）最前
    const isOwnerA = a.owner_id === props.currentUserId
    const isOwnerB = b.owner_id === props.currentUserId
    if (isOwnerA && !isOwnerB) return -1
    if (!isOwnerA && isOwnerB) return 1
    // 2. shared（非 owner 且非 public）其次
    const isSharedA = !a.is_public && !isOwnerA
    const isSharedB = !b.is_public && !isOwnerB
    if (isSharedA && !isSharedB) return -1
    if (!isSharedA && isSharedB) return 1
    // 3. public 最后
    const isPublicA = a.is_public
    const isPublicB = b.is_public
    if (isPublicA && !isPublicB) return 1
    if (!isPublicA && isPublicB) return -1
    // 4. 其他情况按 folder_id 升序
    return a.folder_id - b.folder_id
  })
})

async function addUser() {
  const email = panel.emailToAdd.trim()
  if (!email) return
  try {
    await api.addShareUser(panel.fid, email, 'viewer')   // POST /api/share/{fid}/user
    panel.existing.push({email, role: 'viewer'}) // 默认角色为 viewer
    panel.emailToAdd = ''
  } catch (e) {
    console.error(e)
    alert('Failed to add user')
  }
}
async function updateRole(email: string, role: 'viewer' | 'editor') {
  try {
    // 假设后端接口是 PATCH /api/share/:fid/user/:email/role
    await api.updateShareUserRole(panel.fid, email, role)
    // 成功后 panel.existing 已经是最新的，不用额外处理
  } catch (e) {
    console.error(e)
    alert('Failed to update role')
    // 回滚到原来的值（可选）
    panel.existing = panel.existing.map(u =>
      u.email === email ? { ...u, role: role === 'viewer' ? 'editor' : 'viewer' } : u
    )
  }
}

/* 移除用户邮箱 */
async function removeUser(email: string) {
  try {
    await api.removeShareUser(panel.fid, email) // DELETE /api/share/{fid}/user/{email}
    panel.existing = panel.existing.filter(m => m.email !== email)
  } catch (e) {
    console.error(e)
    alert('Failed to remove user')
  }
}

async function openSetting(fid:number, e:MouseEvent){
  panel.fid = fid
  panel.visible = true
  panel.mode = 'public'
  panel.usersText = ''
  panel.existing = [] 
  // 定位到按钮正下方
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  panel.style = {
    left: rect.left + 'px',
    top : rect.bottom + 6 + 'px'
  }
  // 监听点击外部关闭
  document.addEventListener('click', onClickOutside, { once:true })
    try {
    const perm = await api.getSharePermission(fid)      // 见之前回
    panel.existing  = perm       // 👈 填到只读列表
    panel.mode = await api.getShareMode(fid) ? 'public' : 'specific' // 获取当前模式

    // 可选：如果你想 textarea 里只编辑“新增”用户，就保持空；
    // 如果想直接可编辑，把这行打开：
    // panel.usersText = perm.users.join('\n')
  } catch (e) { console.error(e) }
}
function onClickOutside(evt:MouseEvent){
  if(!(evt.target as HTMLElement).closest('.setting-pop')){
    panel.visible = false
  }
}

function savePermission(){
  emit('update-permission', {
    folder_id: panel.fid,
    mode     : panel.mode,
    users    : panel.usersText
                .split('\n').map(t=>t.trim()).filter(Boolean)
  })
  panel.visible = false
}

function confirmDelete(){
  if (confirm('Delete this shared folder?')){
    emit('remove', panel.fid)
    panel.visible = false
  }
}
</script>

<style scoped>
/* ——— 基础容器保持原设计 ——— */
.shared-sidebar{
  width:260px;height:100%;
  display:flex;flex-direction:column;
  background:#fafbff;border-right:1px solid #e3e7ef;
  overflow:hidden;
}
.shared-sidebar__header{
  position:sticky;top:0;z-index:1;
  background:inherit;padding:.75rem 1rem .5rem;
  border-bottom:1px solid #e3e7ef;
}
.shared-sidebar__header h3{
  margin:0;font-size:.95rem;font-weight:600;color:#374151;
}

.shared-sidebar__list{
  margin:0;padding:.25rem 0;list-style:none;
  overflow-y:auto;flex:1;
}

/* ——— 文件夹行（沿用原 class） ——— */
.shared-sidebar__item{
  --pad-x:.75rem;--pad-y:.45rem;
  display:flex;align-items:center;gap:.45rem;
  padding:var(--pad-y) var(--pad-x);margin:0 .25rem;
  border-radius:6px;cursor:pointer;
  font-size:.93rem;line-height:1.25;
  transition:background .15s,color .15s;
  position:relative;user-select:none;
}
.shared-sidebar__item:hover{background:#eef2ff}
.shared-sidebar__item.is-open{background:#e0e7ff;color:#1e3a8a}
.shared-sidebar__item.is-open::before{
  content:"";position:absolute;left:-.25rem;top:0;bottom:0;width:4px;
  border-radius:0 4px 4px 0;background:#6366f1;
}

/* ——— 文件夹名 / 计数保留原样 ——— */
.shared-sidebar__name{
  flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  font-weight:500;
}
.shared-sidebar__count{
  flex-shrink:0;min-width:1.5em;padding:0 .5em;text-align:center;
  font-size:.8rem;line-height:1.35;border-radius:999px;
  background:#dbeafe;color:#1e3a8a;font-variant-numeric:tabular-nums;
}

/* ——— 展开箭头 ——— */
.chevron{
  width:1rem;text-align:center;flex-shrink:0;
  transition:transform .2s;font-size:.8rem;
}
.chevron.open{transform:rotate(90deg)}  /* 90° 更像展开箭头 */

/* ——— 论文子列表 ——— */
.paper-wrap{
  list-style:none;margin:0;padding:0 0 .5rem 1.55rem;
  border-left:2px solid #e5e7ef;
}
.paper-row{
  font-size:.82rem;line-height:1.3;
  padding:.22rem .25rem;border-radius:4px;cursor:pointer;
  max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; /* 🎯 超长截断 */
  color:#374151;transition:background .15s;
}
.paper-row:hover{background:#f0f4ff}

/* 空 / 加载占位 */
.paper-empty{font-size:.8rem;color:#9ca3af;padding:.25rem 0}

/* 删除按钮沿用原设计 */
.remove-btn{
  background:none;border:none;color:#a1a1aa;
  font-size:1.05rem;cursor:pointer;line-height:1;padding:0 .3rem;
  transition:color .2s;
}
.remove-btn:hover{color:#e11d48}

/* 滚动条细化 */
.shared-sidebar__list::-webkit-scrollbar{width:6px}
.shared-sidebar__list::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:3px}
.shared-sidebar__list:hover::-webkit-scrollbar-thumb{background:#94a3b8}



.setting-btn{
  background:none;border:none;font-size:1rem;
  color:#6b7280;cursor:pointer;padding:0 .3rem;
  transition:color .15s;
}
.setting-btn:hover{ color:#1e3a8a }

.setting-pop{
  position:fixed; z-index:1000;
  min-width:220px; max-width:280px;
  background:#fff; border:1px solid #d1d5db; border-radius:8px;
  box-shadow:0 4px 14px rgba(0,0,0,.1);
  padding:1rem;
  font-size:.87rem;
}
.setting-pop h4{margin:.2rem 0 .6rem;font-size:.9rem}
.radio{display:block;margin-bottom:.25rem;cursor:pointer}
.radio input{margin-right:.4rem}
.users-input textarea{
  width:100%;min-height:60px;font-size:.85rem;
  padding:.35rem .5rem;border:1px solid #d1d5db;border-radius:4px;
  box-sizing:border-box;resize:vertical;margin:.4rem 0 .6rem;
}
.btn-row{display:flex;justify-content:space-between;margin-top:.5rem}
.primary{
  background:#3b82f6;border:none;color:#fff;padding:.35rem .8rem;
  border-radius:4px;font-size:.85rem;cursor:pointer
}
.primary:hover{background:#2563eb}
.danger{
  background:#fff;border:1px solid #ef4444;color:#ef4444;
  padding:.35rem .8rem;border-radius:4px;font-size:.85rem;cursor:pointer
}
.danger:hover{background:#fef2f2}
.row-no{
  display:inline-block;
  min-width:1.4em;          /* 对齐 */
  color:#6b7280;            /* 灰色编号 */
  font-variant-numeric:tabular-nums;
  margin-right:.25em;
}
.paper-row{                /* 仅补上 position 方便 ::before */
  position: relative;
}

/* 高亮效果（颜色与文件夹 is-open 保持一致） */
.paper-row.is-selected{
  background:#e0e7ff;
  color:#1e3a8a;
  font-weight:500;
}
.paper-row.is-selected::before{
  content:"";
  position:absolute;left:-.35rem;top:0;bottom:0;width:3px;
  background:#6366f1;border-radius:0 3px 3px 0;
}
.users-list{
  margin:.5rem 0 0; padding:0; list-style:none;
}
.users-list li{
  font-size:.85rem; color:#374151;
  padding:.12rem 0;
}
.add-user-row{
  display:flex; gap:.4rem; align-items:center; margin-bottom:.4rem;
}
.email-input{
  flex:1; padding:.3rem .5rem; border:1px solid #d1d5db; border-radius:4px;
  font-size:.85rem;
}
.primary.small{ padding:.3rem .7rem; font-size:.8rem; }
.delete-user{
  background:none; border:none; color:#ef4444; cursor:pointer; margin-left:.5rem;
}
.delete-user:hover{ color:#b91c1c; }
.shared-sidebar {
  width: 280px;
  transition: width 0.3s ease;
  /* 其他现有样式 */
}
.shared-sidebar.collapsed {
  width: 0;
  overflow: hidden;
}
.collapse-btn {
  background: none;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  margin-right: 0.5rem;
  /* 可根据需要调整位置和样式 */
}


.shared-sidebar.collapsed {
  width: 60px;        /* 收缩宽度 */
  min-width: 60px;
  max-width: 60px;
}

/* 头部布局微调 */
.collapse-btn {
  background: none;
  border: none;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  margin-right: 4px;
}
.collapse-btn:hover { background: #f0f0f0; }

/* 收缩时隐藏标题文本 */
.shared-sidebar.collapsed .shared-sidebar__header h3 {
  display: none;
}

/* 文件夹行在收缩时居中显示小圆点或自定义图标 */
.shared-sidebar__item.collapsed {
  justify-content: center;
  padding: .45rem 0;
}
/* 收缩时隐藏名称、计数、箭头 */
.shared-sidebar.collapsed .shared-sidebar__name,
.shared-sidebar.collapsed .shared-sidebar__count,
.shared-sidebar.collapsed .chevron,
.shared-sidebar.collapsed .setting-btn {
  display: none;
}

/* 隐藏子论文列表 */
.shared-sidebar.collapsed .paper-wrap {
  display: none;
}

/* “没有数据”提示也隐藏文字，留空白即可 */
.shared-sidebar__empty.collapsed {
  display: none;
}
/* 收缩宽度保持 60px */
.shared-sidebar.collapsed { width: 60px; }

/* 收缩时的文件夹行：居中 + 指针提示 */
.shared-sidebar.collapsed .shared-sidebar__item {
  justify-content: center;
  cursor: pointer;
}

/* 给收缩状态下的每条文件夹行加一个圆点指示 */
.shared-sidebar.collapsed .shared-sidebar__item::after {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9ca3af;       /* 灰色小点，按需改色 */
  display: block;
}

/* Hover / 选中时把圆点和背景同步高亮（可选） */
.shared-sidebar.collapsed .shared-sidebar__item:hover::after,
.shared-sidebar.clas .shared-sidebar__item.is-open::after {
  background: #6366f1;       /* 与选中高亮色保持一致 */
}

/* 已有的隐藏规则继续生效 —— 名称 / 计数 / 箭头 / 设置钮都隐藏 */
.shared-sidebar.collapsed .shared-sidebar__item {
  padding: 0.9rem 0;   /* ↑↑ 行高 ≈ 0.9rem×2 + 字体行高 */
  justify-content: center;
}
.folder-tag{
  font-size:.65rem;
  font-weight:600;
  padding:.1rem .35rem;
  border-radius:4px;
  text-transform:uppercase;
  margin-left:.4rem;
  line-height:1.2;
  letter-spacing:.3px;
}

.folder-tag.owner  { background:#2563eb; color:#fff; }   /* 亮蓝 */
.folder-tag.public { background:#10b981; color:#fff; }   /* 绿 */
.folder-tag.shared { background:#e2e8f0; color:#374151;} /* 灰 */

.shared-sidebar__item.is-open .folder-tag { filter:brightness(0.9); }
.shared-sidebar__item:hover  .folder-tag { filter:brightness(0.95); }
/* 让 header 成为 flex 容器 */
.shared-sidebar__header{
  display: flex;
  align-items: center;
  padding: .75rem 1rem .5rem;   /* 你原来的内边距保留 */
  border-bottom: 1px solid #e3e7ef;
}

/* 折叠按钮保持原样即可，位置在最左 */

/* 标题占满剩余宽度 + 居中 */
.shared-sidebar__header h3{
  flex: 1;              /* 把剩余空间都给 h3 */
  text-align: center;   /* 水平居中 */
  margin: 0;
  font-size: .95rem;
  font-weight: 600;
  color: #374151;
}
/* 1. 调整每一行的布局：左右分布，垂直居中 */
.users-list .user-item {
  display: flex;
  align-items: center;
  justify-content: space-between; /* 邮箱在左，角色和删除按钮在右 */
  padding: 0.3rem 0.5rem;
  border-bottom: 1px solid #e3e7ef;
}

/* 2. 邮箱文字样式 */
.user-item .user-email {
  flex: 1;                 /* 占满剩余空间，长邮箱自动截断 */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.85rem;
  color: #374151;
}

/* 3. 角色选择器美化 */
.role-select {
  margin: 0 0.5rem;        /* 左右间距 */
  padding: 0.2rem 0.4rem;
  font-size: 0.83rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background-color: #fff;
}

/* 给不同角色一个轻微底色区分（可选） */
.role-select option[value="viewer"] {
  background-color: #f9fafb;
}
.role-select option[value="editor"] {
  background-color: #eef2ff;
}

/* 4. 删除按钮对齐和 hover 效果 */
.delete-user {
  background: none;
  border: none;
  font-size: 1rem;
  color: #ef4444;
  cursor: pointer;
}
.delete-user:hover {
  color: #c81e1e;
}

/* 5. 整体弹窗内滚动（当用户太多时） */
.setting-pop .users-input {
  max-height: 200px;       /* 最多显示的高度 */
  overflow-y: auto;
  margin-bottom: 0.5rem;
}

</style>
