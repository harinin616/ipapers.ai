import { reactive } from 'vue';
import api from '../services/api'; 

interface SessionMeta {
  id: string;
  title: string;
  lastMessageAt?: number;
}

interface RwsSession {
  isLoading: boolean;
  processingPaper: boolean;
  sessions: SessionMeta[];
}

class RwsSessionStore {
  state = reactive<RwsSession>({
    isLoading: false,
    processingPaper: false,
    sessions: [],       // empty first, then fetchAllSessions() will fill it
  });

  // get sessions safely
  get sessions(): SessionMeta[] {
    return this.state.sessions || [];
  }

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
      let res: SessionMeta[] = await api.get_rws_sessions();

      res = res.sort((a, b) => (b.lastMessageAt || 0) - (a.lastMessageAt || 0));
      this.state.sessions = Array.isArray(res) ? res : [];
      
      return this.state.sessions;
    } catch (e) {
      console.error('failed to fetch all RWS sessions:', e);
      this.state.sessions = [];
      return [];
    }
  }
      
  async createSession(payload: { title: string }): Promise<SessionMeta> {
    try {
      const newSession: SessionMeta = await api.create_rws_session(payload);
      // insert new session to the front
      if (!this.state.sessions) {
        this.state.sessions = [];
      }
      this.state.sessions.unshift(newSession);
      return newSession;
    } catch (e) {
      console.error('failed to create RWS session:', e);
      throw e;
    }
  }

  async deleteSession(sessionId: string): Promise<void> {
    try {
      await api.delete_rws_session({ session_id: sessionId });
      this.state.sessions = (this.state.sessions || []).filter(s => s.id !== sessionId);
    } catch (e) {
      console.error('failed to delete RWS session:', e);
      throw e;
    }
  }

  async loadMessages(sessionId: string): Promise<any[]> {
    try {
      const res = await api.get_rws_messages({ session_id: sessionId });
      return Array.isArray(res) ? res : [];
    } catch (e) {
      console.error('failed to load RWS messages:', e);
      return [];
    }
  }
}

// create singleton
export const rwsSessionStore = new RwsSessionStore(); 