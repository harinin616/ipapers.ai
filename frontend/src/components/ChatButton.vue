<template>
  <!-- 主按钮：打开弹窗 -->
  <button
    class="action-button chat-button"
    title="Add to file list"
    @click="showModal = true"
  >
    Add&nbsp;to&nbsp;File&nbsp;List
  </button>

  <!-- 弹窗组件，Teleport 到 body -->
  <AddToFoldersModal
    v-if="showModal"
    :paper-id="paperId"
    @added="handleAdded"         
    @close="showModal = false"  
  />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AddToFoldersModal from '../views/AddPaperView.vue'

/* -------- props -------- */
const props = defineProps<{ paperId: string }>()   // 由父层传入的 arXiv id

/* -------- state -------- */
const showModal = ref(false)

/* -------- events -------- */
const handleAdded = () => {
  // 通知全局 FileList 刷新
  window.dispatchEvent(
    new CustomEvent('paper-attached', {
      detail: { paperId: props.paperId }
    })
  )
  showModal.value = false                      // 关闭弹窗
}
</script>

<style scoped>
.action-button{
  padding:.5rem 1rem;border:none;border-radius:4px;
  font-size:.9rem;cursor:pointer;transition:background .2s;
  background:#f0f0f0;color:#333;
}
.action-button:hover{background:#e0e0e0}

.chat-button{background:#3f51b5;color:#fff;}
.chat-button:hover{background:#303f9f}
</style>
