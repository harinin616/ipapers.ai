import { reactive } from 'vue'
import api from '../services/api'

interface FileSelectionState {
  selectedFiles: Set<string>
}

const fileSelectionState = reactive<FileSelectionState>({
  selectedFiles: new Set<string>()
})

export const fileSelectionStore = {
  getSelectedFiles: (): string[] => {
    return Array.from(fileSelectionState.selectedFiles)
  },
  
  isFileSelected: (paperId: string): boolean => {
    return fileSelectionState.selectedFiles.has(paperId)
  },
  
  toggleFileSelection: async (paperId: string) => {
    const isSelected = fileSelectionState.selectedFiles.has(paperId)
    if (isSelected) {
      fileSelectionState.selectedFiles.delete(paperId)
    } else {
      fileSelectionState.selectedFiles.add(paperId)
    }
    await api.update_file_selection({
      paper_id: paperId,
      selected: !isSelected
    })
  },
  setSelection: (ids: string[]) => {
    fileSelectionState.selectedFiles.clear()
    ids.forEach(id => fileSelectionState.selectedFiles.add(id))
  }
  
} 