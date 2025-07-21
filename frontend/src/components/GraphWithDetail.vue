<template>
  <div class="col-wrap">
    <!-- 上 60%：3D 图 -->
    <div class="graph-area">
      <SharedGraph3D :papers="papers" @select-node="onSelectNode" />
    </div>

    <!-- 下 40%：始终渲染 detail-area -->
    <div class="detail-area">
      <template v-if="selected">
        <!-- 已选中，显示详情 -->
        <h3>{{ selected.name }}</h3>
        <p><strong>ID:</strong> {{ selected.id }}</p>
        <p v-if="selected.link">
          <a :href="selected.link" target="_blank">Open PDF</a>
        </p>
      </template>
      <template v-else>
        <!-- 未选中，显示提示 -->
        <div class="placeholder">
          Click a node above to see details here.
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SharedGraph3D from '@/components/SharedGraph3D.vue'

const props = defineProps<{ papers: any[] }>()

const selected = ref<any|null>(null)
function onSelectNode(node: any) {
  selected.value = node
}
</script>

<style scoped>
.col-wrap { display: flex; flex-direction: column; height: 100%; }

.graph-area { flex: 0 0 60%; min-height: 0; }
.detail-area { flex: 0 0 40%; overflow: auto; padding: 1rem; border-top: 1px solid #e5e7eb; }

/* 让 3D 图完全撑满上区 */
.graph-area > * { width: 100%; height: 100%; }

.placeholder { display: flex; align-items: center; justify-content: center; color: #888; height: 100%; }
</style>
