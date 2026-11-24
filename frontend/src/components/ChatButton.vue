<template>
  <!-- 主按钮：打开弹窗 -->
  <button
    :class="['btn', { 'btn-sm': size !== 'md' }]"
    title="Add to file list"
    @click="showModal = true"
  >
    + Add to library
  </button>

  <!-- 弹窗组件，Teleport 到 body -->
  <AddToFoldersModal
    v-if="showModal"
    :paper-id="paperId"
    :platform="platform"
    @added="handleAdded"         
    @close="showModal = false"  
  />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AddToFoldersModal from '../views/AddPaperView.vue'

/* -------- props -------- */
const props = defineProps<{ 
  paperId: string;
  platform?: string;
  size?: 'sm' | 'md';
}>()

/* -------- state -------- */
const showModal = ref(false)

/* -------- events -------- */
const handleAdded = () => {
  // 通知全局 FileList 刷新
  window.dispatchEvent(
    new CustomEvent('paper-attached', {
      detail: { 
        paperId: props.paperId,
        platform: props.platform
      }
    })
  )
  showModal.value = false                      // 关闭弹窗
}
</script>

<style scoped>
/* uses the shared .btn styles from styles/tokens.css */
</style>
