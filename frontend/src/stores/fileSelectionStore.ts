import { reactive } from 'vue'
import api from '../services/api'

interface FileSelectionState {
  selectedFiles: Map<string, string> // paperId -> platform
}

const fileSelectionState = reactive<FileSelectionState>({
  selectedFiles: new Map<string, string>()
})

export const fileSelectionStore = {
  getSelectedFiles: (): Array<{id: string, platform: string}> => {
    return Array.from(fileSelectionState.selectedFiles.entries()).map(([id, platform]) => ({
      id,
      platform
    }))
  },
  
  isFileSelected: (paperId: string): boolean => {
    return fileSelectionState.selectedFiles.has(paperId)
  },
  
  toggleFileSelection: async (paperId: string, platform: string = "arxiv") => {
    const isSelected = fileSelectionState.selectedFiles.has(paperId)
    if (isSelected) {
      fileSelectionState.selectedFiles.delete(paperId)
    } else {
      fileSelectionState.selectedFiles.set(paperId, platform)
    }
    await api.update_file_selection({
      paper_id: paperId,
      platform: platform,
      selected: !isSelected
    })
  },
  setSelection: (items: Array<{id: string, platform: string}>) => {
    fileSelectionState.selectedFiles.clear()
    items.forEach(item => fileSelectionState.selectedFiles.set(item.id, item.platform))
  }
  
} 