<template>
  <div 
    ref="fileListRoot"
    class="files-sidebar" 
    :class="{ 
      'hidden': !showFilesList, 
      'active': showFilesList,
      'pdf-active': showPdf && currentPdfUrl
    }"
  >
    <div v-if="currentPdfUrl && showPdf" class="pdf-view">
      <div class="pdf-header">
        <h3 class="pdf-title" :title="currentFileName">{{ currentFileName }}</h3>
        <div class="pdf-controls">
          <a :href="currentPdfUrl" target="_blank" class="pdf-control-btn" title="Open in new window">
            <svg class="icon-svg" viewBox="0 0 24 24">
              <path d="M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z" />
            </svg>
          </a>
          <button class="close-pdf-btn" @click="closePdf">
            <svg class="icon-svg" viewBox="0 0 24 24">
              <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z" />
            </svg>
          </button>
        </div>
      </div>
      <div class="pdf-loading" v-if="isPdfLoading">
        <div class="loader"></div>
        <div>Loading PDF...</div>
      </div>
<iframe
  v-if="securePdfUrl && showPdf"
  :src="securePdfUrl"
  class="pdf-iframe"
  @load="isPdfLoading = false"
  :style="{ opacity: isPdfLoading ? 0 : 1 }"
  frameborder="0"
>
</iframe>
    </div>
    
    <div v-if="!showPdf || !currentPdfUrl" class="pdf-files-panel"
         @dragover.prevent="handleDragOver"
         @dragleave.prevent="handleDragLeave"
         @drop.prevent="handleDrop">
      <div class="panel-header">
          <h3>File List</h3>

          <!-- 统一放到 .panel-actions 容器中 -->
          <div class="panel-actions">
            <button class="btn new-folder" @click="handleNewFolder" title="New Folder">
              New
            </button>

            <button class="btn upload" @click="openDialog">
              Upload
            </button>

            <router-link to="/chat" class="btn chat">
              Chat
            </router-link>

            <button class="close-btn" @click="toggleFilesList">×</button>
          </div>
        </div>


       
      <!-- Drag and Drop Overlay -->
      <div v-if="isDragging" class="drag-overlay">
        <div class="drag-prompt">
          <svg class="upload-icon" viewBox="0 0 24 24">
            <path d="M9,16V10H5L12,3L19,10H15V16H9M5,20V18H19V20H5Z" />
          </svg>
          <p>Drop PDF files here to upload</p>
        </div>
      </div>

      <!-- 上传进度提示 -->
      <div v-if="uploadingFiles.length > 0" class="upload-progress">
        <div v-for="(file, idx) in uploadingFiles" :key="idx" class="upload-item">
          <span class="upload-filename">{{ file.name }}</span>
          <span class="upload-status">{{ file.status }}</span>
        </div>
      </div>

      <div class="folders-list">
        <div
          v-for="folder in folders"
          :key="folder.id"
          class="folder-block"
        >
          <!-- 文件夹头 -->

                      <div
              class="folder-header"
              :class="{ open: activeFid === folder.id }"
              @click="toggleFolder(folder.id)"
            >
              <!-- 折叠箭头 -->
              <svg class="caret" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>

              <!-- 名称：显示 or 输入框 -->
              <template v-if="editingFolderId !== folder.id">
                <span class="fname" @dblclick.stop="startEditFolder(folder)">{{ folder.name }}</span>
              <span
                v-if="folder.type === 'shared'"
                class="folder-badge"
                title="Shared"
              >S</span>
                <span class="count">({{ folder.files.length }})</span>
                 <button
                   class="f-btn delete"
                   @click.stop="handleDeleteFolder(folder.id)"
                   title="Delete folder"
                 >🗑️</button>
              </template>

              <template v-else>
                <input
                  ref="folderInput"
                  v-model="editingName"
                  class="folder-input"
                  @keydown.enter.stop="saveFolderName(folder)"
                  @keydown.esc.stop="cancelEditFolder"
                  @click.stop
                />
                <!-- 保存 / 取消按钮 -->
                <button class="f-btn save"   @click.stop="saveFolderName(folder)"   title="Save">
                  ✔
                </button>
                <button class="f-btn cancel" @click.stop="cancelEditFolder"         title="Cancel">
                  ✕
                </button>
              </template>

              <!-- 单独的“✎”编辑按钮（非编辑态才显示） -->
              <button
                v-if="editingFolderId !== folder.id"
                class="f-btn edit"
                @click.stop="startEditFolder(folder)"
                title="Rename folder"
              >
                ✎
              </button>
              <button
               v-if="editingFolderId !== folder.id"
               class="f-btn share"
               @click.stop="shareFolder(folder)"
               title="Share folder"
             >🔗</button>
            </div>

          <!-- 论文列表：只渲染当前展开的文件夹 -->
          <transition name="collapse">
            <div
              v-show="activeFid === folder.id"
              class="pdf-files-list"
            >
              <div
                v-for="file in folder.files"
                :key="file.paper_id"
                :class="['pdf-file-item', {active: file.paper_id===selectedFileId}]"
                @click.stop="handleSelectFile(file)"
              >
                <!-- === 以下内容与你原来文件项保持一致 === -->
                      <div class="pdf-file-icon">
                  <svg class="icon-svg" viewBox="0 0 24 24">
                    <path d="M14,2H6C4.9,2 4,2.9 4,4V20C4,21.1 4.9,22 6,22H18C19.1,22 20,21.1 20,20V8L14,2M18,20H6V4H13V9H18V20M10,19L10.9,19C11.2,19 11.3,18.9 11.4,18.7L12.2,17.1L14.3,18.9L15,18.4L12.8,16.6L13.9,15C14.1,14.8 14.2,14.5 14,14.2C13.8,14 13.4,13.9 13,14.1L11.4,15L10.5,12.2L10,12.3L10.6,15.4L9.7,16L9.2,16.5L10,19M13.3,14.7C13.5,14.6 13.6,14.8 13.4,14.9L12,15.8L13.3,14.7M10.8,15.9L11.5,17.2L11.1,16.2L10.8,15.9M11.7,16.3L12.3,15.6L12.3,15.7L11.7,16.3Z" />
                  </svg>
                </div>
                <div class="pdf-file-info">
                  <div class="pdf-file-name">{{ file.filename }}</div>
                </div>
                <button
                  :class="['pdf-file-select',{selected:isFileSelected(file.paper_id)}]"
                  @click.stop="handleToggleSelect(file.paper_id, file.platform || 'arxiv')"
                >
                  <svg class="icon-svg" viewBox="0 0 24 24">
                    <path v-if="isFileSelected(file.paper_id)" d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z" />
                    <path v-else d="M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3M19,5V19H5V5H19Z" />
                  </svg>
                </button>
                <button class="pdf-file-delete"
                        @click.stop="deleteFile(file)">
                  <svg class="icon-svg" viewBox="0 0 24 24">
              <path d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z" />
            </svg>
                </button>
              </div>

              <div v-if="!folder.files.length"
                  class="text-center p-4 text-gray-500">
                Empty
              </div>
            </div>
          </transition>
        </div>
      </div>
      
    

    </div>
     <div v-if="showConfirm" class="confirm-overlay">
      <div class="confirm-box">
        <p>You currently have {{ pdfFiles.length }} files loaded, and the shared list contains {{ pendingShared.length }} files. How would you like to proceed?</p>
        <button @click="applyShared('replace')">Replace</button>
        <button @click="applyShared('merge')">Merge</button>
        <button @click="cancelShared">Cancel</button>
      </div>
    </div>
    <transition name="fade">

    <div v-if="showShareModal" class="confirm-overlay">
      <div class="confirm-box">
        <p>Choose the sharing mode:</p>

        <div class="btn-row">
          <button class="btn primary"
                  @click="confirmShare(true)">
            Public
          </button>

          <button class="btn primary"
                  @click="confirmShare(false)">
            Private
          </button>

          <button class="btn outline"
                  @click="cancelShare">
            Cancel
          </button>
        </div>
      </div>
    </div>
</transition>
    <dialog ref="dlg" class="upload-dialog">
  <form @submit.prevent="submitForm" enctype="multipart/form-data">

    <h3>Upload Paper</h3>

    <div class="field">
      <label>Title</label>
      <input v-model="form.title" placeholder="Optional" />
    </div>

    <div class="field">
      <label>Authors</label>
      <input v-model="form.authors" placeholder="Optional" />
    </div>

    <div class="field">
      <label>Published Date</label>
      <input
        type="date"
        v-model="form.date"
        :max="maxDate"
        placeholder="1900-01-01"
      />
    </div>

    <div class="field">
      <label>Abstract</label>
      <textarea v-model="form.abstract" rows="3" placeholder="Optional"></textarea>
    </div>

    <div class="field">
      <label>PDF File <span class="req">*</span></label>
      <input
        type="file"
        accept="application/pdf,.pdf"
        @change="onFile"
        required
      />
    </div>

    <div class="actions">
      <button type="submit" :disabled="!form.file">Submit</button>
      <button type="button" @click="closeDialog">Cancel</button>
    </div>
  </form>
</dialog>
  <AddPaperView
    v-if="showAddModal"
    :paperId="lastPaperId"
    :platform="lastPlatform"
    @added="loadFolders"
    @close="showAddModal = false"
  />
  </div>
  
</template>

<script lang="ts">
import { defineComponent, ref, watch,computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute , useRouter } from 'vue-router'
import api from '../services/api'
import { fileSelectionStore } from '../stores/fileSelectionStore'
import { reactive } from 'vue'
import AddPaperView from '@/views/AddPaperView.vue'

interface ChatFile {
  file_path: string;
  filename: string;
  paper_id: string;
  platform?: string;
  paper_URL: string;
  added_at: string;
  folder_id: number;
  selected?: boolean; // 可选属性，用于标记是否被选中
}
export interface Folder {
  id: number
  name: string
  type: 'own' | 'shared'
  files: ChatFile[]
}

export default defineComponent({
  name: 'FileList',
  components: { AddPaperView }, 
  
  props: {
    user_id: {
      type: String,
      required: true
    },
    showFilesList: {
      type: Boolean,
      required: true
    },
    showPdf: {
      type: Boolean,
      required: true
    }
  },
  
  emits: [
    'update:showFilesList',
    'file-selected',
    'pdf-closed',
    'files-updated',
    'update-file-count'
  ],
  
  setup(props, { emit }) {
    const pdfFiles = ref<ChatFile[]>([])
    const currentPdfUrl = ref<string | null>(null)
    const showShareModal = ref(false);
    let   pendingShare: { folder: Folder } | null = null;
    const shareFolder = (folder: Folder) => {
      pendingShare = { folder };
      showShareModal.value = true;     // open the 2‑button dialog
    };
    // ...
const showAddModal = ref(false)        // 控制是否显示
const lastPaperId  = ref('')
const lastPlatform = ref<string>('arxiv')     
const dlg  = ref<HTMLDialogElement | null>(null)

// 拖拽上传相关
const isDragging = ref(false)
const uploadingFiles = ref<Array<{ name: string; status: string }>>([])
let dragCounter = 0
const maxDate = new Date().toISOString().slice(0, 10)
const form = reactive({
  title:     '',
  authors:   '',
  date:      '1900-01-01',
  abstract:  '',
  file:      null as File | null
})

function openDialog() {
  resetForm()
  dlg.value?.showModal()
}
function closeDialog() {
  dlg.value?.close()
}
function resetForm() {
  form.title    = ''
  form.authors  = ''
  form.date     = '1900-01-01'
  form.abstract = ''
  form.file     = null
}
function onFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0] || null
  if (f && f.type !== 'application/pdf' && !f.name.endsWith('.pdf')) {
    alert('Please choose a PDF file.')
    (e.target as HTMLInputElement).value = ''
    return
  }
  form.file = f
}

async function submitForm() {
  if (!form.file) return

  const fd = new FormData()
  fd.append('file',        form.file)
  fd.append('title',       form.title)
  fd.append('authors',     form.authors)
  fd.append('published',   form.date || '1900-01-01')
  fd.append('abstract',    form.abstract)

  try {
    const result = await api.upload_file(fd)   // 改成你的接口
    closeDialog()
    lastPaperId.value = result.paper_id
    lastPlatform.value = result.platform || 'upload'
    showAddModal.value = true 

  } catch (e: any) {
    console.error(e)
    const errorMsg = e.response?.data?.detail || e.message || 'Upload failed.'
    alert(`Upload Failed\n\n${errorMsg}\n\nPlease try again.`)
  }
}

// ========== 拖拽上传处理 ==========
const handleDragOver = (e: DragEvent) => {
  e.preventDefault()
  dragCounter++
  if (dragCounter === 1) {
    isDragging.value = true
  }
}

const handleDragLeave = (e: DragEvent) => {
  e.preventDefault()
  dragCounter--
  if (dragCounter === 0) {
    isDragging.value = false
  }
}

const handleDrop = async (e: DragEvent) => {
  e.preventDefault()
  dragCounter = 0
  isDragging.value = false

  const files = Array.from(e.dataTransfer?.files || [])
  const pdfFiles = files.filter(f => f.type === 'application/pdf' || f.name.endsWith('.pdf'))

  if (pdfFiles.length === 0) {
    alert('Please drop PDF files')
    return
  }

  // 批量上传
  for (const file of pdfFiles) {
    await uploadSingleFile(file)
  }
}

// 上传单个文件
const uploadSingleFile = async (file: File) => {
  const uploadItem = { name: file.name, status: 'Uploading...' }
  uploadingFiles.value.push(uploadItem)

  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('title', file.name.replace('.pdf', ''))
    fd.append('authors', '')
    fd.append('published', '1900-01-01')
    fd.append('abstract', '')

    const result = await api.upload_file(fd)
    uploadItem.status = '✓ Success'
    
    // 自动添加到当前文件夹
    if (activeFid.value) {
      await api.attach_to_folder({
        folder_id: activeFid.value,
        paper_id: result.paper_id,
        platform: result.platform || 'upload'
      })
    }

    // 延迟移除上传提示
    setTimeout(() => {
      const idx = uploadingFiles.value.indexOf(uploadItem)
      if (idx > -1) uploadingFiles.value.splice(idx, 1)
    }, 2000)

    // 刷新文件列表
    await loadFolders()
  } catch (e: any) {
    console.error('Upload failed:', e)
    const errorMsg = e.response?.data?.detail || e.message || 'Unknown error'
    uploadItem.status = `✗ Failed: ${errorMsg.substring(0, 30)}...`
    
    // 显示详细错误提示
    alert(`Upload Failed: ${file.name}\n\n${errorMsg}\n\nPlease try again.`)
    
    setTimeout(() => {
      const idx = uploadingFiles.value.indexOf(uploadItem)
      if (idx > -1) uploadingFiles.value.splice(idx, 1)
    }, 5000) // 延长显示时间到5秒
  }
}

  /* ---------- modal handlers ---------- */
  const confirmShare = async (isPublic: boolean) => {
    if (!pendingShare) return;

    try {
      /* 1) 向后端创建 shared_folders 记录 */
      await api.share_folder({
        folder_id: Number(pendingShare.folder.id), // ⬅ 保证是整数
        is_public: isPublic,                             // ⬅ 布尔
      });
      window.dispatchEvent(new Event('share-folder-success'))
    } catch (e) {
      console.error('share failed', e);
    } finally {
      showShareModal.value = false;
      pendingShare = null;
    }
  };


const cancelShare = () => {
  showShareModal.value = false;
  pendingShare = null;
};
    

    const securePdfUrl = computed(() => {
      const url = currentPdfUrl.value
      if (!url) return ''

      // 1. http → https
      let secure = url.startsWith('http://')
        ? url.replace(/^http:\/\//, 'https://')
        : url

      // 2. arxiv.org/pdf 路径重写到 export.arxiv.org/pdf
      if (secure.match(/^https:\/\/arxiv\.org\/pdf\//)) {
        secure = secure.replace(
          /^https:\/\/arxiv\.org\/pdf\//,
          'https://export.arxiv.org/pdf/'
        )
      }

      return secure
    })
    const selectedFileId = ref<string | null>(null)
    const isPdfLoading = ref(false)
    const currentFileName = ref('Document')
    const fileListRoot = ref<HTMLElement | null>(null)
    const route = useRoute()
    const router = useRouter()
    const pendingShared = ref<ChatFile[]>([])
    const showConfirm = ref(false)

    const folders   = ref<Folder[]>([])
    const openSet   = ref<Set<number>>(new Set())   // 展开的 folder.id
    const activeFid = ref<number | null>(null)      // 当前展开的文件夹
    const toggleFolder = (fid: number) => {
      activeFid.value = (activeFid.value === fid) ? null : fid
    }

    const editingFolderId = ref<number | null>(null)
    const editingName     = ref('')
    const folderInput     = ref<HTMLInputElement>()
    const handleNewFolder = async () => {
      try {
        // 1. 调后端创建一个默认名为 "Untitled" 的文件夹
        await api.create_folder({ name: 'Untitled' })
        await loadFolders()
      } catch (err) {
        console.error('create folder failed', err)
      }
    }

    const handleDeleteFolder = async (folderId: number) => {
  if (!confirm('Delete this folder and all its files?')) return
  try {
    await api.delete_folder(folderId)  // 你需要在 api service 里实现这个 DELETE /api/folders/{id}
    folders.value = folders.value.filter(f => f.id !== folderId)
    // 如果删的是当前展开的，切换到第一个
    if (activeFid.value === folderId) {
      activeFid.value = folders.value.length ? folders.value[0].id : null
    }
    // 通知外层更新总数
    const all = folders.value.flatMap(f => f.files)
    emit('files-updated', all)
    emit('update-file-count', all.length)
  } catch (err) {
    console.error('delete folder failed', err)
  }
}

/** 双击名字或点 ✎ 时触发 */
const startEditFolder = async (folder: Folder) => {
  editingFolderId.value = folder.id
  editingName.value     = folder.name
  await nextTick()
  folderInput.value?.focus()
  folderInput.value?.select()
}

/** 保存 */
const saveFolderName = async (folder: Folder) => {
  const newName = editingName.value.trim()
  if (newName === '' || newName === folder.name) {
    cancelEditFolder()
    return
  }
  try {
    await api.rename_folder({ folder_id: folder.id, name: newName })
    folder.name = newName           // 本地立即生效
    cancelEditFolder()
  } catch (e) {
    console.error('rename failed', e)
    alert('Failed to rename folder. Please try again.')
  }
}

/** 取消编辑 */
const cancelEditFolder = () => {
  editingFolderId.value = null
  editingName.value     = ''
}

    const loadFolders = async () => {
      try {
        // 1. 拉取后端
        folders.value = await api.get_user_folders()     // [{id,name,files:[{…}, …]}, …]
        console.log('load folders', folders.value)

        /* 2. 默认展开第一个文件夹 */
        if (folders.value.length) {
          openSet.value.add(folders.value[0].id)
          activeFid.value = folders.value[0].id
        }
        const allFiles: ChatFile[] =
          folders.value.flatMap(f => f.files)
        const selectedItems = allFiles
          .filter(f => f.selected)
          .map(f => ({ id: f.paper_id, platform: f.platform || 'arxiv' }))
        
        fileSelectionStore.setSelection(selectedItems)
        emit('files-updated', allFiles)
        emit('update-file-count', allFiles.length)
      } catch (err) {
        console.error('load folders failed', err)
      }
    }

    const currentFiles = computed<ChatFile[]>(() => {
      const f = folders.value.find(x => x.id === activeFid.value)
      return f ? f.files : []
    })

    
    const handleSelectFile = (file: ChatFile) => {
      isPdfLoading.value = true
      currentFileName.value = file.filename
      currentPdfUrl.value = file.paper_URL
      
      //emit('update:showPdf', true)
      emit('file-selected', file)
      
      if (window.innerWidth <= 768) {
        emit('update:showFilesList', false)
      }
    }
    
    const handleToggleSelect = async (paperId: string, platform: string = 'arxiv') => {
      await fileSelectionStore.toggleFileSelection(paperId, platform)
    }
    
    const isFileSelected = (paperId: string): boolean => {
      return fileSelectionStore.isFileSelected(paperId)
    }
    
   const deleteFile = async (file: ChatFile) => {
  try {
    // 1) 找到要删的 folderId
    const fid = file.folder_id ?? activeFid.value
    if (!fid) throw new Error('No folder selected')

    // 2) 调后端接口
    const ok = await api.remove_file_from_folder(fid, file.paper_id)
    if (!ok) throw new Error('Delete from folder failed')

    // 3) 本地更新：把这个文件从对应 folder.files 里删掉
    const folder = folders.value.find(f => f.id === fid)
    if (folder) {
      folder.files = folder.files.filter(f => f.paper_id !== file.paper_id)
    }

    // 4) 把最新的所有文件列表扁平化，回传给外层
    const allFiles = folders.value.flatMap(f => f.files)
    emit('files-updated', allFiles)
    emit('update-file-count', allFiles.length)

    // 5) 如果正在看的 PDF 被删了，就关闭它
    if (selectedFileId.value === file.paper_id) {
      closePdf()
    }
  } catch (error) {
    console.error('Failed to delete file from folder:', error)
  }
}
    const toggleFilesList = () => {
      emit('update:showFilesList', !props.showFilesList)
      
      if (!props.showFilesList) {
        closePdf()
      }
    }
    
    const closePdf = () => {
      currentPdfUrl.value = null
      selectedFileId.value = null
      isPdfLoading.value = false
      currentFileName.value = 'Document'
      emit('pdf-closed')
      
      if (window.innerWidth <= 768) {
        emit('update:showFilesList', false)
      }
    }
    
    watch(() => props.showFilesList, (newValue) => {
      // Watch logic simplified since we no longer need width updates
    })
    
    onMounted(async () =>  {
      await loadFolders()  
      const shareId = route.params.share_id as string
      if (shareId) {
        const { files } = await api.getShare(shareId)
    //    pendingShared.value = files.map(id => ({
      //    paper_id: id,
        //  filename: id,
          //file_path: '',
        //  paper_URL: '',
         // added_at: '' 
       // }))
        if (pdfFiles.value.length) {
          showConfirm.value = true
        } else {
          await applyShared('merge')
        }
      }
    })

    const shareList = async () => {
      if (!pdfFiles.value.length) return alert('No files to share')
      const ids = pdfFiles.value.map(f => f.paper_id)
      
      const { share_id } = await api.shareFiles({ files: ids })
      const link = `${window.location.origin}/share/${share_id}`
      await navigator.clipboard.writeText(link)
      alert(`Link copied:\n${link}`)
    }
    const applyShared = async (mode: 'replace' | 'merge') => {
      if (mode === 'replace') {
        await api.clear_user_files();
      } 
      const existing = new Set(pdfFiles.value.map(f => f.paper_id));
      const toAttach = mode === 'replace'
      ? pendingShared.value
      : pendingShared.value.filter(f => !existing.has(f.paper_id))

      for (const file of toAttach) {
        await api.attach_paper(file.paper_id);
      }

    //  await loadFiles();

      showConfirm.value = false
      pendingShared.value = []
      emit('files-updated', pdfFiles.value)
      emit('update-file-count', pdfFiles.value.length)
       
  
  // ← 在这里清掉 share_id 路由
      router.replace({ name: 'home' })
    }

    const cancelShared = () => {
      showConfirm.value = false
      pendingShared.value = []
      router.replace({ name: 'home' })
    }
    
    onBeforeUnmount(() => {
      // No cleanup needed anymore
    })
    
    return {
      pdfFiles,
      pendingShared, showConfirm, 
  
      route,shareList, applyShared, cancelShared,loadFolders,toggleFolder,handleDeleteFolder,
       showShareModal,
      shareFolder,
      confirmShare,
      cancelShare,
      currentPdfUrl,
      securePdfUrl,
      selectedFileId,
      isPdfLoading,
      currentFileName,
      fileListRoot,
      handleSelectFile,
      deleteFile,
      toggleFilesList,
      closePdf,
      handleToggleSelect,
       handleNewFolder,
      saveFolderName,
      isFileSelected,
      editingName,
      folders,          // 顶层文件夹数组
      activeFid,        // 当前展开的文件夹 id
      openSet,          // 如果以后还想用折叠集合
      currentFiles,     // 你也许会在别处用到
      startEditFolder,
      editingFolderId,
      cancelEditFolder,
      form,
      maxDate,
      openDialog,
      onFile,
      closeDialog,
      submitForm,
      dlg,
      showAddModal,
      lastPaperId,
      lastPlatform,
      isDragging,
      uploadingFiles,
      handleDragOver,
      handleDragLeave,
      handleDrop,
    }
  }
})
</script>

<style scoped>
.files-sidebar {
  width: 340px;
  height: 100%;
  background-color: var(--surface);
  border-radius: 12px;
  border-left: 2px solid var(--border);
  box-shadow: -3px 0 10px rgba(0, 0, 0, 0.05);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease-in-out, opacity 0.3s ease-in-out;
  flex-shrink: 0;
  will-change: width, opacity;
  transform: translateZ(0);
}

.files-sidebar.pdf-active {
  width: 45%;
  max-width: 750px;
  min-width: 580px;
}


.files-sidebar.hidden {
  width: 0;
  margin: 0;
  padding: 0;
  opacity: 0;
}

.pdf-files-panel {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--surface);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--border);
  background-color: var(--surface-2);
}

.panel-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: var(--text);
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
  color: var(--text-2);
}

.close-btn:hover {
  color: #000;
}

.pdf-files-list {
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  flex: 1;
  overflow-y: auto;
}

.pdf-file-item {
  display: flex;
  align-items: center;
  padding: 0.4rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border);
  width: 100%;
  box-sizing: border-box;
}

.pdf-file-item:hover {
  background-color: var(--surface-2);
  transform: translateY(-2px);
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.08);
}

.pdf-file-item.active {
  background-color: var(--accent-soft);
  border-color: #bbdefb;
}

.pdf-file-icon {
  margin-right: 0.25rem;
  color: #1976d2;
  flex-shrink: 0;
}

.pdf-file-info {
  flex: 1;
  overflow: hidden;
  cursor: pointer;
  min-width: 0;
}

.pdf-file-select {
  background: none;
  border: none;
  color: #757575;
  cursor: pointer;
  padding: 2px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  opacity: 0.7;
  flex-shrink: 0;
  margin-right: 3px;
}

.pdf-file-select:hover {
  background-color: #e8f5e8;
  color: #4caf50;
  opacity: 1;
}

.pdf-file-select.selected {
  background-color: #e8f5e8;
  color: #4caf50;
  opacity: 1;
}

.pdf-file-select.selected:hover {
  background-color: #c8e6c9;
}

.pdf-file-delete {
  background: none;
  border: none;
  color: #757575;
  cursor: pointer;
  padding: 2px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  opacity: 0.7;
  flex-shrink: 0;
}

.pdf-file-delete:hover {
  background-color: #ffebee;
  color: #e53935;
  opacity: 1;
}

.pdf-file-name {
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 0.25rem;
  font-weight: 500;
}

.pdf-file-size {
  font-size: 0.8rem;
  color: #777;
}

/* PDF viewer styles */
.pdf-view {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background-color: var(--surface-2);
  display: flex;
  flex-direction: column;
  border-radius: 6px;
}

.pdf-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background-color: var(--surface-2);
  border-bottom: 1px solid var(--border);
  z-index: 2;
}

.pdf-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pdf-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: calc(100% - 80px);
}

.pdf-control-btn, .close-pdf-btn {
  background-color: transparent;
  border: none;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.pdf-control-btn:hover, .close-pdf-btn:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.pdf-control-btn .icon-svg, .close-pdf-btn .icon-svg {
  width: 18px;
  height: 18px;
  color: var(--text-2);
}

.pdf-loading {
  position: absolute;
  top: 40px;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--surface);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 5;
  gap: 1rem;
}

.pdf-loading .loader {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.pdf-iframe {
  width: 100%;
  height: calc(100% - 40px);
  border: none;
  flex: 1;
  transition: opacity 0.3s ease;
  background-color: var(--surface);
}

.icon-svg {
  width: 20px;
  height: 20px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ───────── Desktop & 超宽屏 ───────── */
@media (min-width: 1600px) {              /* 4K 或 2K 显示器 */
  .files-sidebar.pdf-active {
    width: 50%;           /* 占屏一半 */
    max-width: 900px;     /* 纸面最大宽 */
  }
}

@media (min-width: 1280px) and (max-width: 1599px) { /* 普通 1080p / 1440p */
  .files-sidebar.pdf-active {
    width: 48%;
    max-width: 800px;
  }
}

/* ───────── 中等屏（Laptop） ───────── */
@media (min-width: 1025px) and (max-width: 1279px) {
  .files-sidebar.pdf-active {
    width: 46%;
    min-width: 560px;     /* 原来 500→560，让标题行多出 2~4 字 */
  }
}

/* ───────── Pad / 小屏 Laptop ───────── */
@media (max-width: 1024px) {
  .files-sidebar          { width: 100%; height: 420px; min-width: 0; }
  .files-sidebar.pdf-active { width: 100%; height: 580px; }
  .files-sidebar.hidden   { height: 0; }
}

/* ───────── 手机竖屏 ───────── */
@media (max-width: 768px) {
  .files-sidebar { height: 380px; }
}


.confirm-overlay {
  position: fixed; top: 0; left: 0; right:0; bottom:0;
  background: rgba(0,0,0,0.3);
  display: flex; align-items:center; justify-content:center;
}
.confirm-box {
  background: var(--surface); padding: 1.5rem; border-radius:8px; width:300px;
  text-align: center;
}
.confirm-box button { margin: 0 .5rem; }
.share-btn {
  background: none; border: none; color: var(--accent); cursor: pointer;
  padding: 5px 10px; border-radius:4px; transition: background 0.2s;
}
.share-btn:hover { background: rgba(63,81,181,0.1); }

/* =============== Folder Block =============== */
.folders-list {
  padding: 0.5rem 1rem 1rem;
  overflow-y: auto;
}

/* —— 1. 文件夹标题行 —— */
.folder-header {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 6px;
  font-weight: 600;
  color: var(--text);            /* slate-700 */
  transition: background 0.2s, color 0.2s;
  user-select: none;
}

.folder-header:hover {
  background: var(--surface-2);       /* slate-100 */
  color: var(--text);            /* slate-900 */
}

/* 展开状态 */
.folder-header.open {
  background: var(--accent-soft);       /* indigo-100 */
  color: var(--brand-600);            /* indigo-800 */
}

/* —— 1.1 折叠箭头 —— */
.folder-header .caret {
  width: 14px;
  height: 14px;
  fill: currentColor;
  transition: transform 0.25s;
}

.folder-header.open .caret {
  transform: rotate(90deg);
}

/* —— 1.2 文件数角标 —— */
.folder-header .count {
  margin-left: auto;
  font-size: 0.75rem;
  font-weight: 500;
  background: var(--border);       /* slate-200 */
  color: var(--text);
  padding: 2px 6px;
  border-radius: 9999px;
}

.folder-header.open .count {
  background: #c7d2fe;       /* indigo-200 */
  color: var(--brand-600);
}

/* —— 2. 折叠动画 —— */
.collapse-enter-active,
.collapse-leave-active {
  transition: max-height 0.25s ease;
}

.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  overflow: hidden;
}

/* —— 3. 文件夹外层分隔 —— */
.folder-block + .folder-block {
  margin-top: 0.5rem;
  border-top: 1px solid var(--surface-2); /* slate-100 */
  padding-top: 0.5rem;
}

.folder-header{
  background: var(--surface-2);  
  display:flex;align-items:center;gap:6px;
  padding:6px 10px;border-radius:6px;
  cursor:pointer;transition:background .2s;
}
.folder-header:hover{background:var(--surface-2)}
.folder-header.open {background:#e8f0fe}

.folder-input{
  flex:1;min-width:0;border:1px solid var(--border);
  border-radius:4px;padding:2px 6px;font-size:.92rem;
}
.folder-input:focus{
  outline:none;border-color:#1a73e8;
  box-shadow:0 0 0 2px rgba(26,115,232,.2);
}

/* 小图标按钮 */
.f-btn{
  background:none;border:none;padding:2px 4px;
  cursor:pointer;font-size:.8rem;line-height:1;
  border-radius:4px;color:var(--text-2);
  transition:background .15s,color .15s;
}
.f-btn.edit:hover   {color:#1a73e8;background:#e8f0fe}
.f-btn.save:hover   {color:#4caf50;background:#e8f5e8}
.f-btn.cancel:hover {color:#e53935;background:#ffecec}

.new-folder-btn {
  background: #4caf50;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.2s;
}
.new-folder-btn:hover {
  background: #43a047;
}
.f-btn.delete {
  background: none;
  border: none;
  padding: 2px 4px;
  cursor: pointer;
  color: var(--text-2);                /* 默认灰色 */
  font-size: 0.9rem;
  transition: background 0.2s, color 0.2s;
}
.f-btn.delete:hover {
  color: #e53935;             /* 红色 */
  background: #ffecec;        /* 淡红背景 */
  border-radius: 4px;
}
.f-btn.delete .icon-svg {
  fill: currentColor;
}
/* sidebar scoped css */
.f-btn.share {
  font-size: 1rem;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0 .25rem;
  opacity: .75;
}
.f-btn.share:hover { opacity: 1 }
/* ───────── Share‑Modal 基础 ───────── */
.share-overlay {
  position: fixed;
  inset: 0;                        /* top/right/bottom/left = 0 */
  background: rgba(0,0,0,.45);     /* 暗色蒙版 */
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;                   /* 保证压过侧边栏 / Header */
}

.share-box {
  width: 92%;
  max-width: 420px;
  background: var(--surface);
  border-radius: 14px;
  padding: 2rem 1.75rem 1.5rem;
  box-shadow: 0 6px 24px rgba(0,0,0,.18);
  text-align: center;
  animation: modal-fade-in .25s ease-out;
}

/* 标题 / 文案 */
.share-box h3   { margin: 0 0 .75rem; font-size: 1.2rem; font-weight: 600; color:var(--text) }
.share-box p    { margin: 0 0 1.5rem; color:var(--text-2); line-height: 1.5; }

/* ───────── 按钮区 ───────── */
.share-actions {
  display:flex;
  gap:.85rem;
  justify-content:center;
}

.share-btn {
  flex:1 1 0;
  min-width: 120px;
  padding:.55rem 0;
  border-radius: 9999px;
  font-weight: 500;
  font-size:.95rem;
  cursor:pointer;
  transition: background .18s, color .18s, transform .18s;
}

/* 主按钮 —— confirm */
.share-btn.confirm   {
  background:var(--accent);
  border:1px solid var(--accent);
  color:#fff;
}
.share-btn.confirm:hover { background:#32409b; transform:translateY(-1px); }

/* 次按钮 —— cancel */
.share-btn.cancel    {
  background:var(--surface);
  border:1px solid #bbb;
  color:var(--text-2);
}
.share-btn.cancel:hover { background:#f2f2f2; }

/* ───────── 动画 ───────── */
@keyframes modal-fade-in {
  from { opacity:0; transform:translateY(12px) scale(.96); }
  to   { opacity:1; transform:none; }
}

.btn-row { display: flex; gap: .6rem; justify-content: center; }
.btn.primary     { background:var(--accent); color:#fff; }
.btn.primary:hover { background:var(--brand-600); }
.btn.outline     { border:1px solid var(--border); color:var(--text); }

/* 按钮容器 */
.panel-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* 通用按钮基类 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  font-size: 0.85rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  color: #fff;
}

/* 具体色系 */
.btn.new-folder { background: #4caf50; }       /* 绿色 */
.btn.upload    { background: #ff9800; }        /* 橙色 */
.btn.chat      { background: var(--accent); }        /* 蓝紫色 */

.btn.new-folder:hover { background: #43a047; }
.btn.upload:hover    { background: #fb8c00; }
.btn.chat:hover      { background: var(--brand-600); }

/* 隐藏原生 file input */
.btn.upload input[type="file"] {
  display: none;
}

/* === Panel 顶部工具按钮统一样式 === */
.btn {
  /* 让 <a> 也当按钮渲染 */
  display: inline-flex;
  align-items: center;
  justify-content: center;

  /* 统一尺寸：30 × 30 px，稍微小一点 */
  height: 30px;
  padding: 0 10px;        /* 左右小些即可 */
  font-size: 0.8rem;

  border: none;
  border-radius: 6px;
  cursor: pointer;

  /* 重要：去掉 a 默认下划线 */
  text-decoration: none;

  color: #fff;
  transition: background 0.18s;
}

/* 颜色仍然按原来的 3 个类区分 */
.btn.new-folder { background: #4caf50; }
.btn.upload     { background: #ff9800; }
.btn.chat       { background: var(--accent); }

.btn.new-folder:hover { background:#43a047; }
.btn.upload:hover     { background:#fb8c00; }
.btn.chat:hover       { background:var(--brand-600); }
.upload-dialog{
  padding:1.2rem 1.5rem;
  border:none;border-radius:8px;
  width:320px;
  box-shadow:0 8px 32px rgba(0,0,0,.25);
  font-family:system-ui, sans-serif;
}
.upload-dialog h3{margin-top:0;font-size:1.1rem}

.field{display:flex;flex-direction:column;margin-bottom:.8rem}
.field label{font-size:.8rem;color:var(--text-2);margin-bottom:.25rem}
.field .req{color:#e11d48;font-weight:bold}

.field input[type="file"]{padding:.25rem 0}

.actions{display:flex;justify-content:flex-end;gap:.6rem;margin-top:1rem}
.actions button{
  padding:.35rem .9rem;border:none;border-radius:4px;
  font-size:.85rem;cursor:pointer
}
.actions button[type=submit]{background:var(--brand-600);color:#fff}
.actions button[type=submit]:disabled{opacity:.6;cursor:not-allowed}
.actions button[type=button]{background:var(--border);color:var(--text)}
/* === 修复 Upload 弹窗被吃掉 === */

/* ① 不要再让 .files-sidebar 当 fixed-containing-block */
.files-sidebar{
  /* transform: translateZ(0); */   /* 直接删掉或注释掉 */
  will-change: width, opacity;      /* 性能优化仍在，但不会影响定位 */
  /* overflow: hidden;  这一行可以保留，弹窗已跳出容器就不会再被裁剪 */
}

/* ① 不要让侧栏变成 dialog 的“视口” */
.files-sidebar{
  /* transform: translateZ(0); */   /* ← 注释 / 删除 */
  overflow: visible;                /* ← 让弹窗能溢出来 */
}

/* ② 让 <dialog> 脱离侧栏，固定到窗口中央 */
.upload-dialog{
  position: fixed;          /* 脱离文档流，直接贴在 viewport */
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 3000;            /* 保证在一切侧栏/蒙版之上 */
  /* 下面原本已有的阴影、圆角等保持不变 */
}

/* ③ 给 backdrop 一点暗色 */
.upload-dialog::backdrop{
  background: rgba(0,0,0,.45);
}
.folder-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.2em;
  height: 1.2em;
  font-size: 0.75rem;
  font-weight: bold;
  color: white;
  background-color: #f59e0b; /* 橙黄背景 */
  border-radius: 50%;
  margin-left: 0.5rem;
  cursor: default;
}
.folder-badge:hover {
  background-color: #d97706; /* hover 深一点 */
}

/* ========== 拖拽上传样式 ========== */
.drag-overlay {
  position: absolute;
  top: 60px;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(63, 81, 181, 0.1);
  border: 3px dashed var(--accent);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  pointer-events: none;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}

.drag-prompt {
  text-align: center;
  color: var(--accent);
}

.upload-icon {
  width: 64px;
  height: 64px;
  fill: currentColor;
  margin-bottom: 1rem;
}

.drag-prompt p {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
}

/* 上传进度提示 */
.upload-progress {
  position: absolute;
  top: 70px;
  right: 10px;
  background: var(--surface);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  padding: 0.75rem;
  max-width: 280px;
  z-index: 150;
}

.upload-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0;
  font-size: 0.85rem;
}

.upload-item + .upload-item {
  border-top: 1px solid var(--border);
}

.upload-filename {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 0.5rem;
  color: var(--text);
}

.upload-status {
  font-weight: 600;
  white-space: nowrap;
}

.upload-item .upload-status:contains('Success') {
  color: #10b981;
}

.upload-item .upload-status:contains('Failed') {
  color: var(--danger);
}

.upload-item .upload-status:contains('Uploading') {
  color: var(--accent);
}

</style> 