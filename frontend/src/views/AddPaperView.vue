<template>
  <teleport to="body">
    <div class="modal-backdrop" @click.self="$emit('close')">
      <div class="modal-card">
        <h3 class="modal-title">Add paper to folder(s)</h3>

        <div class="folder-list">
          <label v-for="f in folders" :key="f.id" class="folder-row">
            <input type="checkbox" v-model="selected" :value="f.id"/>
            <span class="folder-name">{{ f.name }} <small class="folder-count">({{ f.files.length }})</small></span>
          </label>
        </div>

        <div class="actions">
          <button class="btn btn-secondary" @click="$emit('close')">Cancel</button>
          <button class="btn btn-primary" :disabled="!selected.length" @click="submit">Add</button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../services/api'
import type { Folder } from '../components/FileList.vue'

const props = defineProps<{ paperId: string }>()
const emit  = defineEmits(['added', 'close'])

const folders   = ref<Folder[]>([])
const selected  = ref<number[]>([])

onMounted(async () => {
  folders.value = await api.get_user_folders()
})

const submit = async () => {
  for (const fid of selected.value) {
    await api.attach_to_folder({ folder_id: fid, paper_id: props.paperId })
  }
  emit('added')
  emit('close')
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal-card {
  background: #fff;
  padding: 1.6rem 2rem;
  border-radius: 8px;
  max-width: 360px;
  width: 90%;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
  display: flex;
  flex-direction: column;
}

.modal-title {
  margin: 0 0 1rem;
  font-size: 1.25rem;
  font-weight: 600;
  text-align: center;
  color: #333;
}

.folder-list {
  max-height: 240px;
  overflow-y: auto;
  margin-bottom: 1rem;
  padding-right: 0.5rem;
}

/* 美化滚动条（Webkit 浏览器） */
.folder-list::-webkit-scrollbar {
  width: 6px;
}
.folder-list::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.1);
  border-radius: 3px;
}
.folder-list::-webkit-scrollbar-track {
  background: transparent;
}

.folder-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0.4rem 0;
  padding: 0.3rem 0.4rem;
  border-radius: 4px;
  transition: background-color 0.15s;
  cursor: pointer;
}
.folder-row:hover {
  background-color: #f5f5f5;
}

.folder-row input[type="checkbox"] {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  accent-color: #3f51b5;
}

.folder-name {
  flex: 1;
  color: #444;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.folder-count {
  color: #888;
  font-size: 0.85rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1rem;
}

/* 按钮基类 */
.btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s, opacity 0.2s;
}

/* 次级按钮 */
.btn-secondary {
  background-color: #e0e0e0;
  color: #333;
}
.btn-secondary:hover {
  background-color: #d5d5d5;
}

/* 主要按钮 */
.btn-primary {
  background-color: #3f51b5;
  color: white;
}
.btn-primary:hover {
  background-color: #303f9f;
}

/* 禁用态 */
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
