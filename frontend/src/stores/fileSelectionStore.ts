import { reactive } from 'vue'

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
  
  toggleFileSelection: (paperId: string) => {
    if (fileSelectionState.selectedFiles.has(paperId)) {
      fileSelectionState.selectedFiles.delete(paperId)
    } else {
      fileSelectionState.selectedFiles.add(paperId)
    }
  }
  
} 