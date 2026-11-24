<template>
  <section class="panel">
    <header>
      <span class="title">Shared Files ({{ files.length }})</span>
      <button @click="$emit('close')" aria-label="Close">×</button>
    </header>

    <div class="file-list" v-if="files.length">
      <div class="file" v-for="f in files" :key="f.paper_id">
        <div class="left">
          <span class="fname">{{ f.filename }}</span>

          <!--<span class="date">{{ formatDate(f.added_at) }}</span>-->
        </div>
        <!--a :href="f.paper_URL" target="_blank">PDF</a-->
         <ChatButton :paper-id="f.paper_id" />

        
      </div>
    </div>

    <p v-else class="empty">
      No files in this folder yet.<br/>
      Please check back later.
    </p>
  </section>
</template>
<script lang="ts" setup>
import { ref, watch } from 'vue'
import api from '@/services/api'
import ChatButton from '@/components/ChatButton.vue'

const props = defineProps<{ shareId: number }>()
defineEmits<{ (e:'close'):void }>()

interface ChatFile {
  file_path: string;
  filename: string;
  paper_id: string;
  paper_URL: string;
  added_at: string;
  folder_id: number;
}

const files = ref<ChatFile[]>([])

async function loadDetail(id: number) {
  const data = await api.get_files_by_folderId(id)
  files.value = data
}

watch(() => props.shareId, id => id && loadDetail(id), { immediate: true })

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>
<style scoped>
.panel {
  flex: 1; display: flex; flex-direction: column; background: var(--surface); border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}

header {
  padding: .75rem 1rem; border-bottom: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center;
}

.title {
  font-weight: 600; font-size: 1rem;
}

.file-list {
  padding: 1rem; overflow-y: auto;
}

.file {
  display: flex; justify-content: space-between; align-items: center;
  padding: .6rem 0; border-bottom: 1px solid #f6f6f6;
}

.left {
  display: flex; flex-direction: column;
}

.fname {
  font-size: .95rem; font-weight: 500;
}

.date {
  font-size: .75rem; color: var(--text-3); margin-top: 2px;
}

.file a {
  color: var(--accent); font-size: .85rem; text-decoration: none;
}

.file a:hover {
  text-decoration: underline;
}

.empty {
  padding: 2rem; text-align: center; color: var(--text-3); font-size: .95rem;
}

button {
  background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-2);
}
button:hover {
  color: #000;
}
</style>
