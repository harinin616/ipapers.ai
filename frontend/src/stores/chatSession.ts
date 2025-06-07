import { reactive, readonly ,ref} from 'vue';
import api from '../services/api'; 

interface SessionMeta {
  id: string;
  title: string;
  // 以后如果需要，可以加更多字段，比如 lastMessageAt, unreadCount 等
}


interface ChatSessionStoreState {
  // 前面已有的：是否正在处理论文相关逻辑
  isLoading: boolean;
  processingPaper: boolean;

  // 新增部分：所有会话列表
  sessions: SessionMeta[];
}



interface ChatSession {
  isLoading: boolean;
  processingPaper: boolean;
}

class ChatSessionStore {
  state = reactive<ChatSession>({
    isLoading: false,
    processingPaper: false,
    sessions: [],       // 一开始为空，后续 fetchAllSessions() 会填充
  });

  // set paper processing state
  setProcessingPaper(isProcessing: boolean): void {
    this.state.processingPaper = isProcessing;
  }

  // get paper processing state
  isProcessingPaper(): boolean {
    return this.state.processingPaper;
  }

  // reset all processing states
  resetProcessingState(): void {
    this.state.processingPaper = false;
  }


  async fetchAllSessions(): Promise<SessionMeta[]> {
    try {
  
 

      let res: SessionMeta[] = await api.get_sessions();

      res = res.sort((a, b) => (b.lastMessageAt || 0) - (a.lastMessageAt || 0));
      this.state.sessions = Array.isArray(res) ? res : [];
      
      return this.state.sessions;
    } catch (e) {
      console.error('fetchAllSessions 出错：', e);
      // 出错时返回空数组
      this.state.sessions = [];
      return [];
    }
  }
      

  async createSession(payload: { title: string }): Promise<SessionMeta> {
    try {
      const newSession: SessionMeta = await api.create_session(payload);
      // 将新会话插入到最前面
      this.state.sessions.unshift(newSession);
      return newSession;
    } catch (e) {
      console.error('createSession 出错：', e);
      throw e;
    }
  }


  async deleteSession(sessionId: string): Promise<void> {
  try {
    await api.delete_session({ session_id: sessionId });
    this.state.sessions = this.state.sessions.filter(s => s.id !== sessionId);
  } catch (e) {
    console.error('deleteSession 出错：', e);
    throw e;
  }
}

async loadMessages(sessionId: string): Promise<any[]> {
  try {
    const res = await api.get_messages({ session_id: sessionId });
    return Array.isArray(res) ? res : [];
  } catch (e) {
    console.error('loadMessages 出错：', e);
    return [];
  }
}
get sessions(): SessionMeta[] {
  return this.state.sessions;
}
  //resetProcessingState(): void {}
  /**
   * 只读暴露其它状态，以备组件中使用
   */
  get processingPaperState(): boolean {
    return this.state.processingPaper;
  }
}

// create singleton
export const chatSessionStore = new ChatSessionStore(); 
