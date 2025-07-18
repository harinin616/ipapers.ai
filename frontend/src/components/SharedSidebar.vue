<template>
  <aside class="shared-sidebar" role="navigation" aria-label="Shared folders">
    <header class="shared-sidebar__header">
      <h3>Public Shared Folders</h3>
    </header>

    <template v-if="shares.length">
      <ul class="shared-sidebar__list">
        <li
          v-for="s in shares"
          :key="s.folder_id"
          class="shared-sidebar__item"
          :class="{ 'is-active': s.folder_id === activeShareId }"
          :title="s.folder_name"
          tabindex="0"
          role="button"
          :aria-selected="s.folder_id === activeShareId"
          @click="$emit('select', s.folder_id)"
          @keyup.enter.space="$emit('select', s.folder_id)"
        >
          <span class="shared-sidebar__name">{{ s.folder_name }}</span>
          <span class="shared-sidebar__count">{{ s.file_cnt }}</span>

          <!-- 删除按钮，只有当前用户是 owner 才显示 -->
          <button
            v-if="s.owner_id === currentUserId"
            class="remove-btn"
            title="Remove folder"
            @click.stop="$emit('remove', s.folder_id)"
          >×</button>
        </li>
      </ul>
    </template>

    <div v-else class="shared-sidebar__empty">No shared folders yet.</div>
  </aside>
</template>

<script lang="ts" setup>
type ShareMeta = {
  id: number
  folder_id: number
  owner_id: string
  is_public: boolean
  folder_name: string
  file_cnt: number
  created_at: string
}

defineProps<{
  shares: ShareMeta[]
  activeShareId: number | null
  currentUserId: string|null
}>()

defineEmits<{
  (e: 'select', folder_id: number): void
  (e: 'remove', folder_id: number): void
}>()
</script>

<style scoped>
.shared-sidebar {
  width: 260px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fafbff;
  border-right: 1px solid #e3e7ef;
  overflow: hidden;
}

.shared-sidebar__header {
  position: sticky;
  top: 0;
  z-index: 1;
  background: inherit;
  padding: 0.75rem 1rem 0.5rem;
  border-bottom: 1px solid #e3e7ef;
}
.shared-sidebar__header h3 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: #374151;
  letter-spacing: .01em;
}

.shared-sidebar__list {
  margin: 0;
  padding: 0.25rem 0;
  list-style: none;
  overflow-y: auto;
  flex: 1;
}

.shared-sidebar__item {
  --pad-x: 0.75rem;
  --pad-y: 0.45rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .5rem;
  padding: var(--pad-y) var(--pad-x);
  margin: 0 .25rem;
  border-radius: 6px;
  font-size: 0.93rem;
  line-height: 1.2;
  cursor: pointer;
  user-select: none;
  color: #1f2937;
  transition: background-color .15s, color .15s;
  outline: none;
  position: relative;
}

.shared-sidebar__item:hover {
  background: #eef2ff;
}
.shared-sidebar__item:focus-visible {
  background: #eef2ff;
  box-shadow: 0 0 0 2px #6366f1;
}
.shared-sidebar__item.is-active {
  background: #e0e7ff;
  color: #1e3a8a;
}
.shared-sidebar__item.is-active::before {
  content: "";
  position: absolute;
  left: -0.25rem;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 0 4px 4px 0;
  background: #6366f1;
}

.shared-sidebar__name {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

.shared-sidebar__count {
  flex-shrink: 0;
  min-width: 1.5em;
  padding: 0 0.5em;
  text-align: center;
  font-size: 0.8rem;
  line-height: 1.35;
  border-radius: 999px;
  background: #dbeafe;
  color: #1e3a8a;
  font-variant-numeric: tabular-nums;
}

.shared-sidebar__empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  color: #9ca3af;
  font-size: 0.9rem;
  text-align: center;
}

/* 删除按钮样式 */
.remove-btn {
  background: none;
  border: none;
  color: #999;
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0 .3rem;
  line-height: 1;
  transition: color 0.2s;
}

.remove-btn:hover {
  color: #e11d48;
}

/* 滚动条 */
.shared-sidebar__list::-webkit-scrollbar {
  width: 6px;
}
.shared-sidebar__list::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.shared-sidebar__list:hover::-webkit-scrollbar-thumb {
  background: #94a3b8;
}
</style>
