<template>
  <div class="share-manager">
    <!-- ① 左侧：我分享出去的文件夹列表 -->
    <SharedSidebar
    :shares="shares"
    :activeShareId="activeId"
    :currentUserId="UserId"
    @select="onSelect"
    @remove="handleRemove"
  />

    <!-- ② 右侧：文件详情 -->
    <FilePanel
      v-if="activeId"
      :share-id="activeId"
      @close="activeId = null"
    />

    <!-- 默认占位 -->
    <div v-else class="placeholder">
      <p>Select a shared folder on the left.</p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/services/api'
import SharedSidebar from '@/components/SharedSidebar.vue'
import FilePanel     from '@/components/FilePanel.vue'
import { User } from 'lucide-vue-next'

const UserId = ref(localStorage.getItem('X-User-ID'))

type ShareMeta = {
  id   : number
  folder_id: number
  owner_id : string
  is_public: boolean
  folder_name: string
  file_cnt   : number
  created_at : string
}

const route   = useRoute()
const router  = useRouter()

const shares  = ref<ShareMeta[]>([])   // 后端返回的列表
const activeId = ref<number | null>(null)

/** 拉我分享的文件夹列表 */
async function loadShares () {
  shares.value = await api.get_shared_folders()  // [{share_id, folder_name, file_cnt, created_at}, ...]
}

/** 点击左侧某项 */
function onSelect (sid: number) {
  activeId.value = sid
//  router.push({ name: 'share-manager', params: { folder_id: sid } })
}
async function handleRemove(folderId: number) {
  const confirmDelete = confirm('Are you sure you want to delete this shared folder?')
  if (!confirmDelete) return

  await api.delete_shared_folder(folderId)
  await loadShares()
}
const reload = async () => {
  console.log('ShareView reload triggered');
  await loadShares()
}

onMounted(async () => {
  window.addEventListener('share-folder-success', reload)
  await loadShares()
})

</script>

<style scoped>
.share-manager {
  display: flex;
  height: calc(100vh - 4rem);   /* 顶部 header 留 4rem */
}
.placeholder {
  flex: 1;
  display:flex;justify-content:center;align-items:center;
  color:#888;font-size:1rem;
}
</style>
