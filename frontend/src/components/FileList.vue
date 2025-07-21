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
    
    <div v-if="!showPdf || !currentPdfUrl" class="pdf-files-panel">
      <div class="panel-header">
        <h3>File List</h3>
          <div style="display: flex; gap: 10px; align-items: center;">
            <button class="new-folder-btn" @click="handleNewFolder" title="New Folder">
               New Folder
            </button>
          <!-- <button class="share-btn" @click="shareList" title="Share file list">
           Share
          </button>-->
            <router-link to="/chat" class="chat-button-inside-sidebar">
              Chat
          </router-link>
        <button class="close-btn" @click="toggleFilesList">×</button>
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
                  @click.stop="handleToggleSelect(file.paper_id)"
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
      <p>
        Do you want to post it to the public Forum now?
      </p>

      <div class="btn-row">
        <button class="btn primary" @click="confirmShare">Confirm</button>
        <button class="btn outline"  @click="cancelShare">Cancel</button>
      </div>
    </div>
  </div>
</transition>
    
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, watch,computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute , useRouter } from 'vue-router'
import api from '../services/api'
import { fileSelectionStore } from '../stores/fileSelectionStore'

interface ChatFile {
  file_path: string;
  filename: string;
  paper_id: string;
  paper_URL: string;
  added_at: string;
  folder_id: number;
  selected?: boolean; // 可选属性，用于标记是否被选中
}
export interface Folder {
  id: number
  name: string
  files: ChatFile[]
}

export default defineComponent({
  name: 'FileList',
  
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

  /* ---------- modal handlers ---------- */
  const confirmShare = async () => {
    if (!pendingShare) return;

    try {
      /* 1) 向后端创建 shared_folders 记录 */
      await api.share_folder({
        folder_id: Number(pendingShare.folder.id), // ⬅ 保证是整数
        is_public: true,                             // ⬅ 布尔
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

        /* 2. 默认展开第一个文件夹 */
        if (folders.value.length) {
          openSet.value.add(folders.value[0].id)
          activeFid.value = folders.value[0].id
        }
        const allFiles: ChatFile[] =
          folders.value.flatMap(f => f.files)
        const selectedIds = allFiles
          .filter(f => (f as any).selected)
          .map(f => f.paper_id)
        
        fileSelectionStore.setSelection(selectedIds)
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
    
    const handleToggleSelect = async (paperId: string) => {
      await fileSelectionStore.toggleFileSelection(paperId)
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
    }
  }
})
</script>

<style scoped>
.files-sidebar {
  width: 340px;
  height: 100%;
  background-color: white;
  border-radius: 12px;
  border-left: 2px solid #e0e0e0;
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
  background-color: white;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #eee;
  background-color: #f9f9f9;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: #333;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
  color: #666;
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
  border: 1px solid #eee;
  width: 100%;
  box-sizing: border-box;
}

.pdf-file-item:hover {
  background-color: #f5f5f5;
  transform: translateY(-2px);
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.08);
}

.pdf-file-item.active {
  background-color: #e3f2fd;
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
  background-color: #f5f5f5;
  display: flex;
  flex-direction: column;
  border-radius: 6px;
}

.pdf-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background-color: #f0f0f0;
  border-bottom: 1px solid #e0e0e0;
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
  color: #333;
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
  color: #555;
}

.pdf-loading {
  position: absolute;
  top: 40px;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.9);
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
  border-top: 4px solid #3f51b5;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.pdf-iframe {
  width: 100%;
  height: calc(100% - 40px);
  border: none;
  flex: 1;
  transition: opacity 0.3s ease;
  background-color: white;
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

.chat-button-inside-sidebar {
  background-color: #3f51b5;
  color: white;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
  text-decoration: none;
  transition: background-color 0.2s ease;
}

.chat-button-inside-sidebar:hover {
  background-color: #303f9f;
}
.confirm-overlay {
  position: fixed; top: 0; left: 0; right:0; bottom:0;
  background: rgba(0,0,0,0.3);
  display: flex; align-items:center; justify-content:center;
}
.confirm-box {
  background: #fff; padding: 1.5rem; border-radius:8px; width:300px;
  text-align: center;
}
.confirm-box button { margin: 0 .5rem; }
.share-btn {
  background: none; border: none; color: #3f51b5; cursor: pointer;
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
  color: #374151;            /* slate-700 */
  transition: background 0.2s, color 0.2s;
  user-select: none;
}

.folder-header:hover {
  background: #f3f4f6;       /* slate-100 */
  color: #111827;            /* slate-900 */
}

/* 展开状态 */
.folder-header.open {
  background: #e0e7ff;       /* indigo-100 */
  color: #3730a3;            /* indigo-800 */
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
  background: #e5e7eb;       /* slate-200 */
  color: #374151;
  padding: 2px 6px;
  border-radius: 9999px;
}

.folder-header.open .count {
  background: #c7d2fe;       /* indigo-200 */
  color: #3730a3;
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
  border-top: 1px solid #f3f4f6; /* slate-100 */
  padding-top: 0.5rem;
}

.folder-header{
  background: #f9fafb;  
  display:flex;align-items:center;gap:6px;
  padding:6px 10px;border-radius:6px;
  cursor:pointer;transition:background .2s;
}
.folder-header:hover{background:#f5f5f5}
.folder-header.open {background:#e8f0fe}

.folder-input{
  flex:1;min-width:0;border:1px solid #ccc;
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
  border-radius:4px;color:#666;
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
  color: #666;                /* 默认灰色 */
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
  background: #fff;
  border-radius: 14px;
  padding: 2rem 1.75rem 1.5rem;
  box-shadow: 0 6px 24px rgba(0,0,0,.18);
  text-align: center;
  animation: modal-fade-in .25s ease-out;
}

/* 标题 / 文案 */
.share-box h3   { margin: 0 0 .75rem; font-size: 1.2rem; font-weight: 600; color:#222 }
.share-box p    { margin: 0 0 1.5rem; color:#555; line-height: 1.5; }

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
  background:#3f51b5;
  border:1px solid #3f51b5;
  color:#fff;
}
.share-btn.confirm:hover { background:#32409b; transform:translateY(-1px); }

/* 次按钮 —— cancel */
.share-btn.cancel    {
  background:#fff;
  border:1px solid #bbb;
  color:#555;
}
.share-btn.cancel:hover { background:#f2f2f2; }

/* ───────── 动画 ───────── */
@keyframes modal-fade-in {
  from { opacity:0; transform:translateY(12px) scale(.96); }
  to   { opacity:1; transform:none; }
}


</style> 