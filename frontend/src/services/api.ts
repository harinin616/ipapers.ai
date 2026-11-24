import axios, { AxiosInstance } from 'axios';
import type { Paper } from '@/types/paper';
import { fileSelectionStore } from '@/stores/fileSelectionStore';

/**
 * API Service interface
 */
export interface IApiService {
  getRecentPapers(limit?: number, keyword?: string, offset?: number): Promise<Paper[]>;
  countPapers(): Promise<number>;
  searchPapers(payload: { query: string, limit?: number, include_summary?: boolean, summary_type?: string }): Promise<any>;
  getUserId(): Promise<string>;
  attach_paper(paperId: string, platform?: string): Promise<boolean>;
  process_embeddings(paperId: string, platform?: string): Promise<boolean>;
  get_user_files(): Promise<any[]>;
  delete_file(paper_id: string, platform?: string): Promise<boolean>;
  stream_chat(payload: { session_id: string; message: string; selected_files: string[] }): Promise<Response>;
  get_paper(paper_id: string, platform?: string): Promise<Paper | null>;
  click_paper(paper_id: string, platform?: string): Promise<boolean>;
  shareFiles(payload: { files: string[] }): Promise<{ share_id: string }>;
  getShare(shareId: string): Promise<{ files: string[] }>;
  clear_user_files(): Promise<void>;
  share_folder (payload: {
    folder_id : number;
    is_public : boolean;
  }): Promise<void>;

  
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
  remove_rws_session_file(session_id: string, paper_id: string, platform?: string): Promise<any>;
  
  // Grant search methods
  improvedGrantSearch(payload: { session_id: string; query: string; conversation_history: any[] }): Promise<any>;
  add_files_to_rws_session(session_id: string, paper_ids: string[]): Promise<any>;
  
  // Graph management methods
  get_paper_graph(session_id: string): Promise<{ nodes: any[], edges: any[] }>;
  update_graph_nodes(papers: any[], session_id: string): Promise<any>;
  add_graph_edge(payload: { from: string; to: string; relationship_type?: string; description?: string; session_id: string }): Promise<any>;
  remove_graph_edge(payload: { from: string; to: string; session_id: string }): Promise<any>;
  complete_graph(session_id: string): Promise<any>;
  
  // Target paper management methods
  set_target_paper(session_id: string, paper_id: string, platform?: string): Promise<any>;
  get_target_paper(session_id: string): Promise<{ target_paper_id: string | null }>;
  clear_target_paper(session_id: string): Promise<any>;

  submitFeedback(payload: { question: string; email?: string }): Promise<{ id: number; created_at: string }>;

  getUserTopics(): Promise<string[]>;
  /** 新增一个 topic */
  addUserTopic(topic: string): Promise<void>;
  /** 删除一个 topic */
  deleteUserTopic(topic: string): Promise<boolean>;

  rename_folder(payload: { folder_id: number; name: string }): Promise<any>;
  create_folder(payload: { name: string }): Promise<any>;
  get_files_by_folderId(folderId: number): Promise<any[]>;

  delete_shared_folder(folderId: number): Promise<void>;

  get_shared_comments(folderId: number): Promise<any[]>;
  add_shared_comment(
    folderId: number,
    content: string
  ): Promise<any>;
  delete_shared_comment(cid: number): Promise<void>;
  get_summary(folderId: number): Promise<string | null>;
  regen_summary(folderId: number): Promise<string | null>;
  getSharePermission(fid:number): Promise<any[]>;
  updateShareMode(folderId: number, is_public: boolean): Promise<void>;
  addShareUser(folderId: number, email: string, role: 'viewer' | 'editor'): Promise<void>;
  removeShareUser(folderId: number, email: string): Promise<void>;
  upload_file(formData: FormData): Promise<any>;
  updateShareUserRole(folderId: number, email: string, role: 'viewer' | 'editor'): Promise<void>;
  get_user_folders(): Promise<Folder[]>;
  get_paper_comments(paperId: string, platform?: string): Promise<any[]>;
  add_paper_comment(paperId: string, content: string, platform?: string): Promise<any>;
  delete_paper_comment(cid: number): Promise<void>;

  // Recommendation methods
  getUserRecommendations(options?: { limit?: number; exclude_existing?: boolean }): Promise<Paper[]>;
  getFolderRecommendations(folderId: number, options?: { limit?: number; exclude_existing?: boolean }): Promise<Paper[]>;
  generateIdeas(payload: GenerateIdeasRequest): Promise<GenerateIdeasResponse>;
  expandProposal(id: string): Promise<{ markdown: string }>;
  streamIdeasGenerate(payload: GenerateIdeasRequest): Promise<Response>;
  getPaperCount(): Promise<number> ;
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
      timeout: 180000, // 3 minutes timeout for full paper analysis
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
          { const t = localStorage.getItem('access_token'); if (t) config.headers['Authorization'] = `Bearer ${t}`; }
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Expired/invalid token: drop the stale session once and reload so a fresh guest session is created.
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error?.response?.status === 401 && localStorage.getItem('access_token') && !sessionStorage.getItem('auth-reset')) {
          sessionStorage.setItem('auth-reset', '1');
          ['access_token', 'X-User-ID', 'user'].forEach((k) => localStorage.removeItem(k));
          window.location.reload();
        }
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
  async getRecentPapers(limit: number = 10, keyword: string = '', offset: number = 0): Promise<Paper[]> {
    try {
      const response = await this.api.get('/api/papers', {
        params: { limit, keyword, offset }
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
   * @param payload { query, limit, include_summary, summary_type }
   * @returns Promise with search results
   */
  async searchPapers(payload: { query: string, limit?: number, include_summary?: boolean, summary_type?: string }): Promise<any> {
    try {
      const response = await this.api.post('/api/search/', {
        query: payload.query,
        limit: payload.limit ?? 30,
        include_summary: payload.include_summary ?? false,
        summary_type: payload.summary_type ?? 'full'
      });
      return response.data;
    } catch (error) {
      console.error('Failed to search papers:', error);
      throw error;
    }
  }

  async generateSearchSummary(payload: { query: string, papers: any[], summary_type?: string }): Promise<any> {
    try {
      const response = await this.api.post('/api/search-summary/', {
        query: payload.query,
        papers: payload.papers,
        summary_type: payload.summary_type ?? 'full'
      });
      return response.data;
    } catch (error) {
      console.error('Failed to generate search summary:', error);
      throw error;
    }
  }
async share_folder(payload: { folder_id: number; is_public: boolean }): Promise<void> {
  try {
    await this.api.post(
      '/api/forum/',
      {
        folder_id: payload.folder_id,   // 整数
        is_public: payload.is_public    
      }
    );
  } catch (error) {
    console.error('Failed to share folder:', error);
    throw error;
  }
}

async delete_shared_folder(folderId: number): Promise<void> {
  try {
    await this.api.delete(`/api/forum/${folderId}`);
  } catch (error) {
    console.error('Failed to delete shared folder:', error);
    throw error;
  }
}

async get_shared_folders(): Promise<any[]> {
  try {
    const response = await this.api.get('/api/forum/');
    return response.data;
  } catch (error) {
    console.error('Failed to get shared folders:', error);
    throw error;
  }
}

  /**
   * Get a new user ID
   * @returns Promise with user ID data
   */
  async getUserId(): Promise<string> {
    try {
      // Server issues a guest identity plus a signed token; the token is what authenticates later calls.
      const response = await this.api.post('/api/user/guest');
      const { user_id, access_token } = response.data;
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('X-User-ID', user_id);
      return user_id;
    } catch (error) {
      console.error('Failed to get user ID:', error);
      throw error;
    }
  }

  async attach_paper(paperId: string, platform?: string): Promise<boolean> {
    try {
      const response = await this.api.post(`/api/chat/attach_paper`, {
      "paper_id": paperId,
      "platform": platform || "arxiv"
    });
      return response.data;
    } catch (error) {
      console.error('Failed to associate paper with chat:', error);
      throw error;
    } 
  }

  async process_embeddings(paperId: string, platform?: string): Promise<boolean> {
    try {
      const response = await this.api.post(`/api/chat/process_embeddings`, { 
        paper_id: paperId,
        platform: platform
      });
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

  async delete_file(paper_id: string, platform?: string): Promise<boolean> {
    try {
      let url = `/api/chat/files/delete/${paper_id}`;
      if (platform) {
        url += `?platform=${platform}`;
      }
      const response = await this.api.delete(url);
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
        { const t = localStorage.getItem('access_token'); if (t) headers['Authorization'] = `Bearer ${t}`; }
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
        { const t = localStorage.getItem('access_token'); if (t) headers['Authorization'] = `Bearer ${t}`; }
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

  async get_paper(paper_id: string, platform?: string): Promise<Paper | null> {
    try {
      const response = await this.api.post(`/api/chat/get_paper`, {
        "paper_id": paper_id,
        "platform": platform || "arxiv"
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get paper:', error);
      throw error;
    }
  }

  async click_paper(paper_id: string, platform?: string): Promise<boolean> {
    try {
      let url = `/api/papers/click/${paper_id}`;
      if (platform) {
        url += `?platform=${platform}`;
      }
      const response = await this.api.post(url);
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
  
  async update_file_selection(payload: { paper_id: string; platform?: string; selected: boolean }): Promise<any> {
    const userId = localStorage.getItem('X-User-ID');
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    if (userId) {
      headers['X-User-ID'] = userId;
      { const t = localStorage.getItem('access_token'); if (t) headers['Authorization'] = `Bearer ${t}`; }
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
        { const t = localStorage.getItem('access_token'); if (t) headers['Authorization'] = `Bearer ${t}`; }
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
  async rename_folder(payload: { folder_id: number; name: string }) {
    const resp = await this.api.patch('/api/folders/rename', payload)
    return resp.data
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

  async remove_rws_session_file(session_id: string, paper_id: string, platform?: string): Promise<any> {
    try {
      let url = `/api/review/sessions/${session_id}/files/${paper_id}`;
      if (platform) {
        url += `?platform=${platform}`;
      }
      const response = await this.api.delete(url);
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
  
  async set_target_paper(session_id: string, paper_id: string, platform?: string): Promise<any> {
    try {
      const response = await this.api.post('/api/review/target_paper', { 
        session_id, 
        paper_id,
        platform
      });
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
 async getUserTopics(): Promise<string[]> {
    try {
      const resp = await this.api.get('/api/topics');
      return resp.data?.topics ?? [];
    } catch (err) {
      console.error('Failed to get user topics:', err);
      throw err;
    }
  }

  /** POST /api/topics  body: { topic } */
  async addUserTopic(topic: string): Promise<void> {
    try {
      await this.api.post('/api/topics', { topic });
    } catch (err) {
      console.error(`Failed to add topic "${topic}":`, err);
      throw err;
    }
  }

  /** DELETE /api/topics/{topic} → 后端返回 { ok: boolean } */
  async deleteUserTopic(topic: string): Promise<boolean> {
    try {
      const resp = await this.api.delete(`/api/topics/${encodeURIComponent(topic)}`);
      return resp.data?.ok ?? true;          // 默认返回 true 视为成功
    } catch (err) {
      console.error(`Failed to delete topic "${topic}":`, err);
      return false;
    }
  }
  async get_user_folders(): Promise<Folder[]> {
    const resp = await this.api.get('/api/folders')
    return resp.data  // [{id,name,files:[...]}, ...]
  }
  async attach_to_folder(data: { folder_id: number; paper_id: string; platform?: string }) {
  return await this.api.post(`/api/folders/${data.folder_id}/files`, {
    paper_id: data.paper_id,
    platform: data.platform
  })
}
  async remove_file_from_folder(folderId: number, paperId: string, platform?: string): Promise<boolean> {
    let url = `/api/folders/${folderId}/files/${paperId}`;
    if (platform) {
      url += `?platform=${platform}`;
    }
    const resp = await this.api.delete(url);
    return resp.status === 204;
  }
  async create_folder(payload: { name: string }) {
    try {
      const resp = await this.api.post('/api/folders/', payload)
      return resp.data
    } catch (error) {
      console.error('Failed to create folder:', error)
      throw error
    }
  }
  async delete_folder(folderId: number) {
  await this.api.delete(`/api/folders/${folderId}`)
}
  async get_files_by_folderId(folderId: number): Promise<any[]> {
    try {
      const resp = await this.api.get(`/api/folders/${folderId}/files`)
      return resp.data
    } catch (error) {
      console.error('Failed to get files by folder ID:', error)
      throw error
    }
  }
  async get_shared_comments(folderId: number): Promise<any[]> {
    try{
      console.log('Fetching shared comments for folder ID:', folderId)
      const resp=await this.api.get(`/api/comments/shared/${folderId}`)
      return resp.data
    }catch(error){
      console.error('Failed to get shared comments:', error)
      throw error
    }
  }
  async add_shared_comment(
    folderId: number,
    content: string
  ): Promise<any> {
    try {
      const resp = await this.api.post(`/api/comments/shared`, {
        folderId,
        content
      })
      return resp.data
    } catch (error) {
      console.error('Failed to add shared comment:', error)
      throw error
    }
  }
  async delete_shared_comment(cid: number): Promise<void> {
    try {
      await this.api.delete(`/api/comments/shared/${cid}`);
    } catch (error) {
      console.error('Failed to delete shared comment:', error);
      throw error;
    }
  }
  async get_summary(folderId: number): Promise<string | null> {
    try {
      const resp = await this.api.get(`/api/folders/${folderId}/summary`);
      return resp.data?.summary ?? null;
    } catch (error) {
      console.error('Failed to get folder summary:', error);
      throw error;
    }
  }
  async regen_summary(folderId: number): Promise<string | null> {
    try {
      const resp = await this.api.post(`/api/folders/${folderId}/summary/regenerate`);
      return resp.data?.summary ?? null;
    } catch (error) {
      console.error('Failed to regenerate folder summary:', error);
      throw error;
    }
  }
  async getSharePermission(fid:number): Promise<any[]> {
    try {
      const resp = await this.api.get(`/api/forum/${fid}/permission`);
      return resp.data;
    } catch (error) {
      console.error('Failed to get share permission:', error);
      throw error;
    }
  }
  async updateShareMode(folderId: number, is_public: boolean): Promise<void> {
    try {
      await this.api.patch(`/api/forum/${folderId}/mode`, { is_public });
    } catch (error) {
      console.error('Failed to update share mode:', error);
      throw error;
    }
  }
  async getShareMode(folderId: number): Promise<boolean> {
    try {
      const resp = await this.api.get(`/api/forum/${folderId}/mode`);
      return resp.data;
    } catch (error) {
      console.error('Failed to get share mode:', error);
      throw error;
    }
  }
  async addShareUser(folderId: number, email: string, role: 'viewer' | 'editor'): Promise<void> {
    try {
      await this.api.post(`/api/forum/${folderId}/add_user`, { email, role });
    } catch (error) {
      console.error('Failed to add share user:', error);
      throw error;
    }
  }
  async updateShareUserRole(folderId: number, email: string, role: 'viewer' | 'editor'): Promise<void> {
    try {
      await this.api.patch(`/api/forum/${folderId}/update_user_role`, { email, role });
    } catch (error) {
      console.error('Failed to update share user role:', error);
      throw error;
    }
  }
  async removeShareUser(folderId: number, email: string): Promise<void> {
    try {
      await this.api.delete(`/api/forum/${folderId}/remove_user`, { data: { email } });
    } catch (error) {
      console.error('Failed to remove share user:', error);
      throw error;
    }
  }
  async upload_file(formData: FormData): Promise<any> {
    try {
      const res = await this.api.post(`/api/upload/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      return res.data
    } catch (err) {
      console.error('Upload failed:', err)
      throw err
    }
  }
  async get_paper_comments(paperId: string, platform: string = 'arxiv'): Promise<any[]>{
    try {
      const resp = await this.api.get(`/api/comments/paper/${encodeURIComponent(paperId)}`, {
        params: { platform }
      })
      return resp.data
    } catch (error) {
      console.error('Failed to get paper comments:', error)
      throw error
    }
  }

  async add_paper_comment(paperId: string, content: string, platform: string = 'arxiv'): Promise<any>{
    try {
      const resp = await this.api.post(`/api/comments/paper`, {
        paperId,
        content,
        platform
      })
      return resp.data
    } catch (error) {
      console.error('Failed to add paper comment:', error)
      throw error
    }
  }

  async delete_paper_comment(cid: number): Promise<void>{
    try {
      await this.api.delete(`/api/comments/paper/${cid}`)
    } catch (error) {
      console.error('Failed to delete paper comment:', error)
      throw error
    }
  }

  // Improved Conversational Search methods
  async improvedConversationalSearch(payload: {
    session_id: string;
    query: string;
    conversation_history: any[]
  }): Promise<any> {
    try {
      const response = await this.api.post('/api/improved-conversational/search', payload)
      return response.data
    } catch (err) {
      console.error('Failed to perform improved conversational search:', err)
      throw err
    }
  }

  async analyzePaper(payload: {
    paper_id: string;
    platform: string;
  }): Promise<any> {
    try {
      const response = await this.api.post('/api/improved-conversational/analyze-paper', payload)
      return response.data
    } catch (err) {
      console.error('Failed to analyze paper:', err)
      throw err
    }
  }

  // Grant search methods
  async improvedGrantSearch(payload: {
    session_id: string;
    query: string;
    conversation_history: any[]
  }): Promise<any> {
    try {
      const response = await this.api.post('/api/improved-grant-search/search', payload)
      return response.data
    } catch (err) {
      console.error('Failed to perform improved grant search:', err)
      throw err
    }
  }

  async getSearchSuggestions(params: { 
    session_id: string; 
    context?: string 
  }): Promise<any> {
    try {
      const response = await this.api.get('/api/conversational/search_suggestions', { params })
      return response.data
    } catch (err) {
      console.error('Failed to get search suggestions:', err)
      throw err
    }
  }

  // Recommendation methods
  async getUserRecommendations(options: { limit?: number; exclude_existing?: boolean } = {}): Promise<Paper[]> {
    try {
      const params = new URLSearchParams()
      if (options.limit) params.append('limit', options.limit.toString())
      if (options.exclude_existing !== undefined) params.append('exclude_existing', options.exclude_existing.toString())

      const response = await this.api.get(`/api/recommendations/user?${params.toString()}`)
      return response.data
    } catch (err) {
      console.error('Failed to get user recommendations:', err)
      throw err
    }
  }

  async getFolderRecommendations(folderId: number, options: { limit?: number; exclude_existing?: boolean } = {}): Promise<Paper[]> {
    try {
      const params = new URLSearchParams()
      if (options.limit) params.append('limit', options.limit.toString())
      if (options.exclude_existing !== undefined) params.append('exclude_existing', options.exclude_existing.toString())

      const response = await this.api.get(`/api/recommendations/folder/${folderId}?${params.toString()}`)
      return response.data
    } catch (err) {
      console.error('Failed to get folder recommendations:', err)
      throw err
    }
  }
  async generateIdeas(payload: GenerateIdeasRequest): Promise<GenerateIdeasResponse> {
    try {
      const resp = await this.api.post('/api/ideas/generate', payload)
      return resp.data
    } catch (err) {
      console.error('Failed to generate ideas:', err)
      throw err
    }
  }
    // ---- Streaming Ideation ----
  async streamIdeasGenerate(payload: GenerateIdeasRequest): Promise<Response> {
    try {
      const userId = localStorage.getItem('X-User-ID');
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (userId) headers['X-User-ID'] = userId;

      // SSE/streaming endpoint
      const resp = await fetch(`/api/ideas/stream_generate`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });
      return resp;
    } catch (err) {
      console.error('Failed to stream ideas generation:', err);
      throw err;
    }
  }


  async expandProposal(id: string): Promise<{ markdown: string }> {
    try {
      const resp = await this.api.post('/api/ideas/expand', { id })
      return resp.data
    } catch (err) {
      console.error('Failed to expand proposal:', err)
      throw err
    }
  }

}
interface ChatFile {
  file_path: string
  filename:  string
  paper_id:  string
  platform?: string
  paper_URL: string
  added_at:  string
  folder_id: number
  selected?: boolean;
}
// Export singleton instance
export default new ApiService(); 
export interface Folder {
  id: number
  name: string
  type: 'own' | 'shared'
  files: ChatFile[]
}

// ---- Types aligned with the frontend ----
export interface Persona {
  key: string
  name: string
  on: boolean
}

export interface Idea {
  id: string
  title: string
  summary: string
  novelty: number
  feasibility: number
  clarity: number
  score: number
  tags: string[]
}

export interface GenerateIdeasRequest {
  topic: string
  rounds: number
  reviewers: number
  personas: Persona[]
}

export interface GenerateIdeasResponse {
  ideas: Idea[]
  kpis?: { nonDup?: number; pAt10?: number }
}
