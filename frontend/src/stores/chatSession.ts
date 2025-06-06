import { reactive, readonly ,ref} from 'vue';
import api from '../services/api'; 

interface SessionMeta {
  id: string;
  title: string;
  // 以后如果需要，可以加更多字段，比如 lastMessageAt, unreadCount 等
}

const _sessions = ref<SessionMeta[]>([
]);



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
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(_sessions.value);
      }, 200); // 模拟 200ms 延迟
    });
  }
  /*
  async fetchAllSessions(): Promise<SessionMeta[]> {
    try {
      // 调用后端接口
      const res: SessionMeta[] = await api.get_sessions();
      // 将拿到的结果写入到 state.sessions
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
  }*/
  async createSession(payload: { title: string }): Promise<SessionMeta> {
    return new Promise((resolve) => {
      setTimeout(() => {
        const newSession: SessionMeta = {
          id: Date.now().toString(),
          title: payload.title,
        };
        _sessions.value.unshift(newSession);
        resolve(newSession);
      }, 200);
    });
  }

  async deleteSession(sessionId: string): Promise<void> {
    return new Promise((resolve) => {
      setTimeout(() => {
        const idx = _sessions.value.findIndex((s) => s.id === sessionId);
        if (idx !== -1) {
          _sessions.value.splice(idx, 1);
        }
        resolve();
      }, 200);
    });
  }

async loadMessages(sessionId: string): Promise<any[]> {
    return new Promise((resolve) => {
      setTimeout(() => {
        // 你可以根据 sessionId 返回不同的 mock 数据
        resolve([]);
      }, 200);
    });
  }
  get sessions(): SessionMeta[] {
   return _sessions.value;
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
