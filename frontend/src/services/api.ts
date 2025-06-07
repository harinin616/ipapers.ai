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

  get_sessions(): Promise<{ id: string; title: string }[]>;
  create_session(payload: { title: string }): Promise<{ id: string; title: string }>;
  delete_session(payload: { session_id: string }): Promise<any>;
  get_messages(payload: { session_id: string }): Promise<any[]>;
  update_session_title(payload: { session_id: string; title: string }): Promise<any>;
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

}

// Export singleton instance
export default new ApiService(); 