import axios, { AxiosInstance } from 'axios';
import type { Paper } from '@/types/paper';
import { fileSelectionStore } from '@/stores/fileSelectionStore';

/**
 * API Service interface
 */
export interface IApiService {
  getRecentPapers(limit?: number, offset?: number): Promise<Paper[]>;
  countPapers(): Promise<number>;
  searchPapers(payload: { query: string, limit?: number }): Promise<any>;
  getUserId(): Promise<string>;
  attach_paper(paperId: string): Promise<boolean>;
  process_embeddings(paperId: string): Promise<boolean>;
  get_user_files(): Promise<any[]>;
  delete_file(paper_id: string): Promise<boolean>;
  stream_chat(payload: { session_id: string; message: string; selected_files: string[] }): Promise<Response>;
  get_paper(paper_id: string): Promise<boolean>;
  click_paper(paper_id: string): Promise<boolean>;
  shareFiles(payload: { files: string[] }): Promise<{ share_id: string }>;
  getShare(shareId: string): Promise<{ files: string[] }>;
  clear_user_files(): Promise<void>;

  
  // Session management methods
  get_sessions(): Promise<{ id: string; title: string }[]>;
  create_session(payload: { title: string }): Promise<{ id: string; title: string }>;
  delete_session(payload: { session_id: string }): Promise<any>;
  get_messages(payload: { session_id: string }): Promise<any[]>;
  update_session_title(payload: { session_id: string; title: string }): Promise<any>;
  
  // RWS (Review) functionality
  chat_rwg(message: string): Promise<Response>;
  
  // RWS Session management methods
  get_rws_sessions(): Promise<{ id: string; title: string }[]>;
  create_rws_session(payload: { title: string }): Promise<{ id: string; title: string }>;
  delete_rws_session(payload: { session_id: string }): Promise<any>;
  get_rws_messages(payload: { session_id: string }): Promise<any[]>;
  update_rws_session_title(payload: { session_id: string; title: string }): Promise<any>;
  stream_rws(payload: { session_id: string; message?: string; selected_files: string[]; guidance?: string[] }): Promise<Response>;
  
  // RWS File upload
  upload_rws_file(session_id: string, file: File): Promise<any>;
  get_rws_session_files(session_id: string): Promise<any[]>;
  remove_rws_session_file(session_id: string, paper_id: string): Promise<any>;
  add_files_to_rws_session(session_id: string, paper_ids: string[]): Promise<any>;
  
  // Graph management methods
  get_paper_graph(session_id: string): Promise<{ nodes: any[], edges: any[] }>;
  update_graph_nodes(papers: any[], session_id: string): Promise<any>;
  add_graph_edge(payload: { from: string; to: string; relationship_type?: string; description?: string; session_id: string }): Promise<any>;
  remove_graph_edge(payload: { from: string; to: string; session_id: string }): Promise<any>;
  complete_graph(session_id: string): Promise<any>;
  
  // Target paper management methods
  set_target_paper(session_id: string, paper_id: string): Promise<any>;
  get_target_paper(session_id: string): Promise<{ target_paper_id: string | null }>;
  clear_target_paper(session_id: string): Promise<any>;

  submitFeedback(payload: { question: string; email?: string }): Promise<{ id: number; created_at: string }>;
}
/**
 * API Service implementation
 */
class ApiService implements IApiService {
  private api: AxiosInstance;
  
  constructor() {
    // Create axios instance
    this.api = axios.create({
      baseURL: '',  
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add a request interceptor to include user_id in headers
    this.api.interceptors.request.use(
      (config) => {
        const userId = localStorage.getItem('X-User-ID');
        if (userId) {
          config.headers['X-User-ID'] = userId;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );
  }

  /**
   * Get recent papers 
   * @param limit Number of papers to retrieve
   * @param offset Pagination offset
   * @returns Promise with array of papers
   */
  async getRecentPapers(limit: number = 10, offset: number = 0): Promise<Paper[]> {
    try {
      const response = await this.api.get('/api/papers', {
        params: { limit, offset }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get recent papers:', error);
      throw error;
    }
  }

  /**
   * Count total papers in database
   * @returns Promise with paper count
   */
  async countPapers(): Promise<number> {
    try {
      const response = await this.api.get('/api/papers/count');
      return response.data;
    } catch (error) {
      console.error('Failed to count papers:', error);
      throw error;
    }
  }

  
  /**
   * Search papers by query
   * @param payload { query, limit }
   * @returns Promise with search results
   */
  async searchPapers(payload: { query: string, limit?: number }): Promise<any> {
    try {
      const response = await this.api.post('/api/search/', {
        query: payload.query,
        limit: payload.limit ?? 30
      });
      return response.data;
    } catch (error) {
      console.error('Failed to search papers:', error);
      throw error;
    }
  }

  /**
   * Get a new user ID
   * @returns Promise with user ID data
   */
  async getUserId(): Promise<string> {
    try {
      const response = await this.api.post('/api/user/get_id');
      return response.data;
    } catch (error) {
      console.error('Failed to get user ID:', error);
      throw error;
    }
  }

  async attach_paper(paperId: string): Promise<boolean> {
    try {
      const response = await this.api.post(`/api/chat/attach_paper`, { paper_id: paperId });
      return response.data;
    } catch (error) {
      console.error('Failed to associate paper with chat:', error);
      throw error;
    } 
  }

  async process_embeddings(paperId: string): Promise<boolean> {
    try {
      const response = await this.api.post(`/api/chat/process_embeddings`, { paper_id: paperId });
      return response.data;
    } catch (error) {
      console.error('Failed to process embeddings:', error);
      throw error;
    }
  }

  async get_user_files(): Promise<any[]> {
    try {
      const response = await this.api.get(`/api/chat/files`);
      return response.data;
    } catch (error) {
      console.error('Failed to get user files:', error);
      throw error;
    }
  }

  async delete_file(paper_id: string): Promise<boolean> {
    try {
      const response = await this.api.delete(`/api/chat/files/delete/${paper_id}`);
      return response.data;
    } catch (error) {
      console.error('Failed to delete file:', error);
      throw error;
    }
  }

  async stream_chat(payload: { session_id: string; message: string; selected_files: string[] }): Promise<Response> {
    try {
      const userId = localStorage.getItem('X-User-ID');
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (userId) {
        headers['X-User-ID'] = userId;
      }

      const response = await fetch(`/api/chat/stream_chat`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });

      return response;
    } catch (error) {
      console.error('Failed to stream chat:', error);
      throw error;
    }
  }

  async chat_rwg(message: string): Promise<Response> {
    try {
      const userId = localStorage.getItem('X-User-ID');
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (userId) {
        headers['X-User-ID'] = userId;
      }

      const selectedFiles = fileSelectionStore.getSelectedFiles();

      const response = await fetch(`/api/review/chat_rwg`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ message: message, selected_files: selectedFiles })
      });
      
      return response; 
    } catch (error) {
      console.error('Failed to chat RWG:', error);
      throw error;
    }
  }

  async get_paper(paper_id: string): Promise<boolean> {
    try {
      const response = await this.api.post(`/api/chat/get_paper`, { paper_id: paper_id });
      return response.data;
    } catch (error) {
      console.error('Failed to get paper:', error);
      throw error;
    }
  }

  async click_paper(paper_id: string): Promise<boolean> {
    try {
      const response = await this.api.post(`/api/papers/click/${paper_id}`);
      return response.data;
    } catch (error) {
      console.error('Failed to click paper:', error);
      throw error;
    }
  }

  /**
   * 获取所有会话列表
   */
  async get_sessions(): Promise<{ id: string; title: string }[]> {
    try {
      const response = await this.api.get('/api/chat/sessions');
      return response.data;
    } catch (error) {
      console.error('Failed to get sessions:', error);
      throw error;
    }
  }

  /**
   * 新建会话
   */
  async create_session(payload: { title: string }): Promise<{ id: string; title: string }> {
    try {
      const response = await this.api.post('/api/chat/sessions', payload);
      return response.data;
    } catch (error) {
      console.error('Failed to create session:', error);
      throw error;
    }
  }
  
  async delete_session(payload: { session_id: string }): Promise<any> {
    try {
      const response = await this.api.delete('/api/chat/sessions', { data: payload });
      return response.data;
    } catch (error) {
      console.error('Failed to delete session:', error);
      throw error;
    }
  }

  /**
   * 获取指定会话的消息
   */
  async get_messages(payload: { session_id: string }): Promise<any[]> {
    try {
      const response = await this.api.get('/api/chat/messages', { params: payload });
      return response.data;
    } catch (error) {
      console.error('Failed to get messages:', error);
      throw error;
    }
  }
  
  async update_session_title(payload: { session_id: string; title: string }): Promise<any> {
    try {
      const response = await this.api.post('/api/chat/update_session_title', payload);
      return response.data;
    } catch (error) {
      console.error('Failed to update session title:', error);
      throw error;
    }
  }
  
  async update_file_selection(payload: { paper_id: string; selected: boolean }): Promise<any> {
    const userId = localStorage.getItem('X-User-ID');
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    if (userId) {
      headers['X-User-ID'] = userId;
    }
    const response = await fetch('/api/chat/update_file_selection', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    });
    return response.json();
  }
  async shareFiles(payload: { files: string[] }): Promise<{ share_id: string }> {
    const resp = await this.api.post('/api/share', payload);
    return resp.data;
  }

  /** ② 根据 shareId 拉取文件列表 */
  async getShare(shareId: string): Promise<{ files: string[] }> {
    const resp = await this.api.get(`/api/share/${shareId}`);
    return resp.data;
  }

  
  // ============ RWS SESSION MANAGEMENT ============
  
  async get_rws_sessions(): Promise<{ id: string; title: string }[]> {
    try {
      const response = await this.api.get('/api/review/sessions');
      return response.data;
    } catch (error) {
      console.error('Failed to get RWS sessions:', error);
      throw error;
    }
  }

  async create_rws_session(payload: { title: string }): Promise<{ id: string; title: string }> {
    try {
      const response = await this.api.post('/api/review/sessions', payload);
      return response.data;
    } catch (error) {
      console.error('Failed to create RWS session:', error);
      throw error;
    }
  }
  
  async delete_rws_session(payload: { session_id: string }): Promise<any> {
    try {
      const response = await this.api.delete('/api/review/sessions', { data: payload });
      return response.data;
    } catch (error) {
      console.error('Failed to delete RWS session:', error);
      throw error;
    }
  }

  async get_rws_messages(payload: { session_id: string }): Promise<any[]> {
    try {
      const response = await this.api.get('/api/review/messages', { params: payload });
      return response.data;
    } catch (error) {
      console.error('Failed to get RWS messages:', error);
      throw error;
    }
  }
  
  async update_rws_session_title(payload: { session_id: string; title: string }): Promise<any> {
    try {
      const response = await this.api.post('/api/review/update_session_title', payload);
      return response.data;
    } catch (error) {
      console.error('Failed to update RWS session title:', error);
      throw error;
    }
  }

  async stream_rws(payload: { session_id: string; message?: string; selected_files: string[]; guidance?: string[] }): Promise<Response> {
    try {
      const userId = localStorage.getItem('X-User-ID');
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (userId) {
        headers['X-User-ID'] = userId;
      }

      const response = await fetch(`/api/review/stream_rws`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });

      return response;
    } catch (error) {
      console.error('Failed to stream RWS:', error);
      throw error;
    }
  }

  // ============ GRAPH MANAGEMENT ============
  
  async get_paper_graph(session_id: string): Promise<{ nodes: any[], edges: any[] }> {
    try {
      const response = await this.api.get('/api/review/graph', { params: { session_id } });
      return response.data;
    } catch (error) {
      console.error('Failed to get paper graph:', error);
      throw error;
    }
  }

  async update_graph_nodes(papers: any[], session_id: string): Promise<any> {
    try {
      const response = await this.api.post('/api/review/graph/nodes', { papers, session_id });
      return response.data;
    } catch (error) {
      console.error('Failed to update graph nodes:', error);
      throw error;
    }
  }

  async add_graph_edge(payload: { from: string; to: string; relationship_type?: string; description?: string; session_id: string }): Promise<any> {
    try {
      const response = await this.api.post('/api/review/graph/edges', payload);
      return response.data;
    } catch (error) {
      console.error('Failed to add graph edge:', error);
      throw error;
    }
  }

  async remove_graph_edge(payload: { from: string; to: string; session_id: string }): Promise<any> {
    try {
      const response = await this.api.delete('/api/review/graph/edges', { data: payload });
      return response.data;
    } catch (error) {
      console.error('Failed to remove graph edge:', error);
      throw error;
    }
  }

  async complete_graph(session_id: string): Promise<any> {
    try {
      const response = await this.api.post('/api/review/graph/complete', { session_id });
      return response.data;
    } catch (error) {
      console.error('Failed to complete graph:', error);
      throw error;
    }
  }

  // RWS File upload
  async upload_rws_file(session_id: string, file: File): Promise<any> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_id', session_id);

      const response = await this.api.post(`/api/review/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Failed to upload RWS file:', error);
      throw error;
    }
  }

  async get_rws_session_files(session_id: string): Promise<any[]> {
    try {
      const response = await this.api.get(`/api/review/sessions/${session_id}/files`);
      return response.data;
    } catch (error) {
      console.error('Failed to get RWS session files:', error);
      throw error;
    }
  }

  async remove_rws_session_file(session_id: string, paper_id: string): Promise<any> {
    try {
      const response = await this.api.delete(`/api/review/sessions/${session_id}/files/${paper_id}`);
      return response.data;
    } catch (error) {
      console.error('Failed to remove RWS session file:', error);
      throw error;
    }
  }

  async add_files_to_rws_session(session_id: string, paper_ids: string[]): Promise<any> {
    try {
      const response = await this.api.post(`/api/review/sessions/${session_id}/add_files`, {
        paper_ids: paper_ids
      });
      return response.data;
    } catch (error) {
      console.error('Failed to add files to RWS session:', error);
      throw error;
    }
  }
   async clear_user_files(): Promise<void> {
    try {
      await this.api.post('/api/chat/files/clear');
    } catch (error) {
      console.error('Failed to clear user files:', error);
      throw error;
    }
  }

  // ============ TARGET PAPER MANAGEMENT ============
  
  async set_target_paper(session_id: string, paper_id: string): Promise<any> {
    try {
      const response = await this.api.post('/api/review/target_paper', { session_id, paper_id });
      return response.data;
    } catch (error) {
      console.error('Failed to set target paper:', error);
      throw error;
    }
  }

  async get_target_paper(session_id: string): Promise<{ target_paper_id: string | null }> {
    try {
      const response = await this.api.get('/api/review/target_paper', { params: { session_id } });
      return response.data;
    } catch (error) {
      console.error('Failed to get target paper:', error);
      throw error;
    }
  }

  async clear_target_paper(session_id: string): Promise<any> {
    try {
      const response = await this.api.delete('/api/review/target_paper', { data: { session_id } });
      return response.data;
    } catch (error) {
      console.error('Failed to clear target paper:', error);
      throw error;
    }
  }
  async submitFeedback(payload: { question: string; email?: string }): Promise<{ id: number; created_at: string }> {
    try {
      const resp = await this.api.post('/api/contact', payload);
      return resp.data;
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      throw error;
    }
  }
}

// Export singleton instance
export default new ApiService(); 