import os
import logging
import torch
from transformers import AutoModel, AutoTokenizer
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APITimeoutError, APIError
import dashscope
from http import HTTPStatus
from google import genai
import ast


DAILY_LIMIT = int(os.getenv("LLM_CALLS_PER_DAY", "2000"))
HOURLY_LIMIT = int(os.getenv("LLM_CALLS_PER_HOUR", "500"))
logger = logging.getLogger(__name__)


class ConvLLMService:
    """
    General LLM Service Client
    """
    
    def __init__(self):
        """Initialize LLM service"""
        # api key and url
        self.embedding_api_key = os.getenv("EMBEDDING_API_KEY", "")
        
        self.api_url = os.getenv("EMBEDDING_API_URL", "")

        self.llm_api_key = os.getenv("LLM_API_KEY", "")

        # default models and settings
        
        self.conversation_model = os.getenv("LLM_CONVERSATION_MODEL", "") 
        self.query_model = os.getenv("LLM_QUERY_MODEL", "")

        #self.default_embedding_model = os.getenv("LLM_EMBEDDING_MODEL", "") 
        self.default_embedding_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
        self.BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", ""))

        self.rerank_model=os.getenv("LLM_RERANK_MODEL","")
        self.rerank_topn=int(os.getenv("LLM_RERANK_TOPN", "10"))

     #   self.embedding_client = AsyncOpenAI(
      #      api_key=self.embedding_api_key,
       #     base_url=self.api_url
        #)

        #if not self.embedding_client:
         #   raise ValueError("embedding client failed to initialize")
        
        # Only initialize Gemini client if API key is provided
        if self.llm_api_key:
            self.llm_client = genai.Client(api_key=self.llm_api_key)
        else:
            self.llm_client = None
            logger.warning("LLM_API_KEY not provided, Gemini client not initialized")

        # initialize call limits
        self.hourly_calls = 0
        self.last_call_hour = self.current_hour_str() 
        self.daily_calls = 0
        self.last_call_date = datetime.now().strftime('%Y-%m-%d')
        self.call_limit_lock = asyncio.Lock()
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)

        ...
        # ↓↓↓ 新增 ↓↓↓
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = os.getenv("SPECTER2_MODEL", "allenai/specter2_base")

        # trust_remote_code=True 让 Transformers 自动加载 Specter2 自定义类
        self.specter_tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.specter_model = (
            AutoModel
            .from_pretrained(model_name, trust_remote_code=True)
            .to(self._device)
            .eval()
        )
        # 用 FP16 可省显存
        if self._device == "cuda":
            self.specter_model = self.specter_model.half()


    def save_daily_calls(self, date: str, calls: int):
        """Save daily call count to file"""
        try:
            call_log_file = self.data_dir / "llm_daily_calls.log"
            with open(call_log_file, 'a', encoding='utf-8') as f:
                f.write(f"{date},{calls}\n")
            logger.info(f"Saved daily calls for {date}: {calls}")
        except Exception as e:
            logger.error(f"Failed to save daily calls: {e}")

    @staticmethod
    def current_hour_str() -> str:
        return datetime.now().strftime('%Y-%m-%d-%H')
    
    def save_hourly_calls(self, hour_str: str, calls: int):
        try:
            call_log_file = self.data_dir / "llm_hourly_calls.log"
            with call_log_file.open('a', encoding='utf-8') as f:
                f.write(f"{hour_str},{calls}\n")
            logger.info(f"Saved hourly calls for {hour_str}: {calls}")
        except Exception as e:
            logger.error(f"Failed to save hourly calls: {e}")
        
    async def get_conversation_completion(
        self,
        messages: List[Dict[str, str]],
        stream: Optional[bool] = True,
        model: Optional[str] = None 
    ) -> Optional[Any]:
        """
        call chat model to generate response
        """
        convo_model = model or self.conversation_model

        try:
            # Check daily call limit with thread safety
            async with self.call_limit_lock:
                current_hour = self.current_hour_str()
                if current_hour != self.last_call_hour:
                    # Save previous hour's call count before resetting
                    if self.hourly_calls > 0:
                        self.save_hourly_calls(self.last_call_hour, self.hourly_calls)

                    self.hourly_calls = 0
                    self.last_call_hour = current_hour

                if self.hourly_calls >= HOURLY_LIMIT:
                    logger.error("Hourly call limit exceeded")
                    return None

                self.hourly_calls += 1


                current_date = datetime.now().strftime('%Y-%m-%d')
                if current_date != self.last_call_date:
                    # Save previous day's call count before resetting
                    if self.daily_calls > 0:
                        self.save_daily_calls(self.last_call_date, self.daily_calls)
                    
                    # Reset for new day
                    self.daily_calls = 0
                    self.last_call_date = current_date
                
                if self.daily_calls >= DAILY_LIMIT:
                    logger.error("Daily call limit exceeded")
                    return None
                
                # Increment call counter before making the call
                self.daily_calls += 1
            
            # Convert OpenAI format messages to Gemini format
            gemini_contents = self._convert_messages_to_gemini_format(messages)
            
            if stream:
                # streaming mode
                response = await self.llm_client.aio.models.generate_content_stream(
                    model=convo_model,
                    contents=gemini_contents
                )
            else:
                # non-streaming mode
                response = await self.llm_client.aio.models.generate_content(
                    model=convo_model,
                    contents=gemini_contents
                )
            
            return response
            
        except Exception as e:
             logger.error(f"Error occurred when calling Gemini API for conversation: {e.__class__.__name__} - {e}")
             return None


    async def get_conversation_completion_non_streaming(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None
    ) -> Optional[str]:
        """
        调用对话模型，非流式，一次性拿到完整文本。
        返回值：生成的文本（str），失败返回 None
        """
        convo_model = model or self.conversation_model

        try:
            # ---- 限流逻辑（原样保留） ----
            async with self.call_limit_lock:
                current_hour = self.current_hour_str()
                if current_hour != self.last_call_hour:
                    if self.hourly_calls > 0:
                        self.save_hourly_calls(self.last_call_hour, self.hourly_calls)
                    self.hourly_calls = 0
                    self.last_call_hour = current_hour

                HOURLY_LIMIT = 100  # 你自己的常量
                if self.hourly_calls >= HOURLY_LIMIT:
                    logger.error("Hourly call limit exceeded")
                    return None
                self.hourly_calls += 1

                current_date = datetime.now().strftime('%Y-%m-%d')
                if current_date != self.last_call_date:
                    if self.daily_calls > 0:
                        self.save_daily_calls(self.last_call_date, self.daily_calls)
                    self.daily_calls = 0
                    self.last_call_date = current_date

                DAILY_LIMIT = 1000  # 你自己的常量
                if self.daily_calls >= DAILY_LIMIT:
                    logger.error("Daily call limit exceeded")
                    return None
                self.daily_calls += 1
            # ---- /限流逻辑 ----

            # 转 Gemini 格式
            gemini_contents = self._convert_messages_to_gemini_format(messages)

            # **非流式调用**
            resp = await self.llm_client.aio.models.generate_content(
                model=convo_model,
                contents=gemini_contents
            )

            # 提取纯文本
            text = self._gemini_text(resp)
            return text

        except Exception as e:
            logger.error(
                f"Error occurred when calling Gemini API for conversation: "
                f"{e.__class__.__name__} - {e}"
            )
            return None

    # --------- 辅助函数 ---------
    def _gemini_text(self, resp) -> str:
        """
        尝试从 Gemini 非流式返回对象中抽取文本。
        兼容 resp.text / resp.candidates[].content.parts[].text 两种方式。
        """
        # 1) 大部分 SDK 都会有 resp.text
        if hasattr(resp, "text") and isinstance(resp.text, str):
            return resp.text

        # 2) 兜底：从 candidates 结构里拼接
        try:
            parts = []
            for c in getattr(resp, "candidates", []) or []:
                content = getattr(c, "content", None)
                if not content:
                    continue
                for p in getattr(content, "parts", []) or []:
                    t = getattr(p, "text", None)
                    if t:
                        parts.append(t)
            return "".join(parts)
        except Exception:
            # 再兜底直接 str()，以免把复杂对象抛回前端
            return str(resp)

    def _convert_messages_to_gemini_format(self, messages: List[Dict[str, str]]) -> str:
        """
        Convert OpenAI format messages to Gemini format
        """
        try:
            # Extract all user and assistant messages and combine them
            conversation_parts = []
            for message in messages:
                role = message.get("role", "")
                content = message.get("content", "")
                
                if role == "user":
                    conversation_parts.append(f"User: {content}")
                elif role == "assistant":
                    conversation_parts.append(f"Assistant: {content}")
                elif role == "system":
                    conversation_parts.append(f"System: {content}")
            
            # Join all parts with newlines
            gemini_content = "\n".join(conversation_parts)
            
            # for single user message, return just the content
            if len(messages) == 1 and messages[0].get("role") == "user":
                gemini_content = messages[0].get("content", "")
                
            return gemini_content
            
        except Exception as e:
            logger.error(f"Error converting messages to Gemini format: {e}")
            if messages:
                return messages[-1].get("content", "")
            return ""
        except RateLimitError as e:
            logger.error(f"Embedding API rate limit exceeded: {e}")
            return None
        except APITimeoutError as e:
            logger.error(f"Embedding API timeout: {e}")
            return None
        except APIConnectionError as e:
            logger.error(f"Embedding API connection error: {e}")
            return None
        except APIError as e:
            logger.error(f"Embedding API error: {e}")
            return None
        except Exception as e: 
             logger.error(f"Unknown error occurred when calling LLM API (Embeddings): {e.__class__.__name__} - {e}")
             return None

    # llm_service.py
    from typing import Sequence, List, Union
    import torch

    TextLike = Union[str, dict]  # 你也可能收到 dict

    def _norm(self, texts: Sequence[TextLike]) -> List[str]:
        """
        只留下非空字符串；若元素是 dict，则用其 'text' 字段。
        """
        normed: List[str] = []
        for i, t in enumerate(texts):
            if isinstance(t, str):
                s = t.strip()
            elif isinstance(t, dict) and 'text' in t and isinstance(t['text'], str):
                s = t['text'].strip()
            else:
                # 记录一下是哪条脏数据，然后跳过
                logger.warning(f"Skip invalid chunk at idx {i}: {repr(t)[:120]}")
                continue
            if s:                      # 过滤空白
                normed.append(s)
        return normed

    async def get_embeddings(
        self,
        texts: List[str]
    ) -> Optional[List[List[float]]]:
        texts = self._norm(texts)           # ★ 先归一化
        if not texts:
            return []
            
        try:
            batch_size = self.BATCH_SIZE 
            total_texts = len(texts)
            total_batches = (total_texts + batch_size - 1) // batch_size
            

            all_embeddings = []
            
            # Process batches serially
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_idx = i // batch_size
                
                batch_embeddings = self._sync_embed(batch)
                all_embeddings.append(batch_embeddings)

            # Concatenate all batches and convert to Python list
            embeddings = torch.cat(all_embeddings, dim=0).cpu().tolist()
            logger.info(f"Successfully generated embeddings for all {total_texts} texts")
            return embeddings
        except Exception as e:
            logger.error(f"Specter2 embedding error: {e.__class__.__name__} - {e}")
            return None

        # 同类中新增一个同步 helper
    def _sync_embed(self, batch: List[str]) -> torch.Tensor:
        with torch.inference_mode():
            inputs = self.specter_tokenizer(
                batch,
                truncation=True,
                padding=True,
                max_length=self.specter_model.config.max_position_embeddings,
                return_tensors="pt"
            ).to(self._device)
            outputs = self.specter_model(**inputs)
                # Specter-2 把 CLS 位置池化到 pooler_output
            vecs = outputs.pooler_output  # (batch, 768)
            return vecs.detach()

            

    async def get_rerank(
        self,
        documents:List[str],
        query:str
    ) -> List[int]:
        dashscope.api_key = self.embedding_api_key
        response = dashscope.TextReRank.call(
        model="gte-rerank-v2",
        query=query,
        documents=documents,
        top_n=self.rerank_topn,
        return_documents=True
        )
        if response.status_code == HTTPStatus.OK:
            # Return the sorted indices from the results
            return [result['index'] for result in response.output['results']]
        return []

    # ========== Conversational Search Methods ==========
    
    async def conversation(
        self,
        messages: List[dict],
        model: Optional[str] = None
    ) -> str:
        """
        General conversation method using Gemini
        """
        try:
            if not self.llm_client:
                logger.warning("LLM client not available")
                return ""
            
            convo_model = model or self.conversation_model
            if not convo_model:
                convo_model = "gemini-2.5-flash"
            
            # Convert messages to Gemini format
            gemini_messages = []
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'user':
                    gemini_messages.append({"role": "user", "parts": [{"text": content}]})
                elif role == 'assistant':
                    gemini_messages.append({"role": "model", "parts": [{"text": content}]})
                elif role == 'system':
                    # Gemini doesn't have system messages, prepend to user message
                    if gemini_messages and gemini_messages[-1]["role"] == "user":
                        gemini_messages[-1]["parts"][0]["text"] = f"System: {content}\n\nUser: {gemini_messages[-1]['parts'][0]['text']}"
                    else:
                        gemini_messages.append({"role": "user", "parts": [{"text": f"System: {content}"}]})
            
            # Use the correct Gemini API call
            response = self.llm_client.models.generate_content(
                model=convo_model,
                contents=gemini_messages
            )
            
            return response.text if response and response.text else ""
            
        except Exception as e:
            logger.error(f"Error in conversation: {e}")
        
            err_str = str(e)

            if "{" in err_str:
                try:
                    dict_part = err_str[err_str.index("{"):]  # substring starting from first '{'
                    err_dict = ast.literal_eval(dict_part)    # safely parse into dict
                    error_msg = err_dict.get("error", {}).get("message", "")
                    return f"Extracted error message: {error_msg}"  # interpolates variable
                except Exception as parse_err:
                    logger.warning(f"Failed to parse error details: {parse_err}")
                    return ""
            else:
                return ""


        
    
    async def enhance_search_query(
        self,
        original_query: str,
        context: str
    ) -> str:
        """
        Enhance search query with conversation context
        """
        try:
            prompt = f"""
You are a search query enhancement expert. Your task is to improve the user's search query by incorporating relevant context from their conversation history.

Context from conversation:
{context}

Original query: {original_query}

Please enhance the query by:
1. Resolving any pronouns or references (e.g., "this paper" → specific paper title)
2. Adding relevant keywords from the conversation context
3. Maintaining the user's original search intent
4. Making the query more specific and searchable

Return only the enhanced query, nothing else.
"""
            
            enhanced_query = await self.conversation(
                messages=[{"role": "user", "content": prompt}]
            )
            
            return enhanced_query.strip() if enhanced_query else original_query
            
        except Exception as e:
            logger.error(f"Error enhancing search query: {e}")
            return original_query
    
    async def rerank_with_context(
        self,
        papers: List[str],
        context: str
    ) -> List[int]:
        """
        Rerank papers based on conversation context
        """
        try:
            prompt = f"""
You are a research paper ranking expert. Based on the user's conversation context, rank the following papers in order of relevance.

Context from conversation:
{context}

Papers to rank (title and abstract):
{chr(10).join([f"{i+1}. {paper}" for i, paper in enumerate(papers)])}

Please return only the indices (1-based) of the papers in order of relevance, separated by commas.
For example: 3,1,5,2,4

Return only the numbers, nothing else.
"""
            
            response = await self.conversation(
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response:
                return list(range(len(papers)))
            
            # Parse the response to get indices
            try:
                indices = [int(x.strip()) - 1 for x in response.split(',')]
                # Filter valid indices
                valid_indices = [i for i in indices if 0 <= i < len(papers)]
                # Add any missing indices
                for i in range(len(papers)):
                    if i not in valid_indices:
                        valid_indices.append(i)
                return valid_indices
            except:
                return list(range(len(papers)))
                
        except Exception as e:
            logger.error(f"Error reranking with context: {e}")
            return list(range(len(papers)))
    
    async def generate_search_suggestions(
        self,
        current_query: str,
        search_results: List[dict],
        context: str
    ) -> List[str]:
        """
        Generate follow-up search suggestions
        """
        try:
            # Handle both dict and object formats
            result_titles = []
            for result in search_results[:3]:
                if isinstance(result, dict):
                    title = result.get('title', 'Unknown')
                else:
                    title = getattr(result, 'title', 'Unknown')
                result_titles.append(f"- {title}")
            
            prompt = f"""
You are a research assistant helping users explore academic papers. Based on the current search and results, suggest follow-up questions.

Current search: {current_query}

Top search results:
{chr(10).join(result_titles)}

Context:
{context}

Generate 3-5 follow-up search suggestions that would help the user explore related topics or refine their search. Focus on:
1. Related research areas
2. Specific aspects of the current topic
3. Alternative approaches or methodologies
4. Recent developments or trends

Return each suggestion on a new line, starting with "- ".
"""
            
            response = await self.conversation(
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response:
                return []
            
            # Parse suggestions
            suggestions = []
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    suggestions.append(line[2:])
                elif line and len(suggestions) < 5:
                    suggestions.append(line)
            
            return suggestions[:5]
            
        except Exception as e:
            logger.error(f"Error generating search suggestions: {e}")
            return []
    
    async def generate_conversation_summary(
        self,
        conversation_history: List[dict],
        current_query: str,
        context: str
    ) -> str:
        """
        Generate a summary of the current conversation
        """
        try:
            # Extract user queries from history
            user_queries = [msg.get('content', '') for msg in conversation_history if msg.get('role') == 'user']
            
            prompt = f"""
You are a research assistant. Generate a brief summary of this search session.

User's search history: {', '.join(user_queries)}
Current query: {current_query}

Context:
{context}

Generate a brief summary (1-2 sentences) highlighting the user's research interests and search patterns.
"""
            
            summary = await self.conversation(
                messages=[{"role": "user", "content": prompt}]
            )
            
            return summary.strip() if summary else f"Search session with {len(user_queries)} queries"
            
        except Exception as e:
            logger.error(f"Error generating conversation summary: {e}")
            return f"Search session with {len(conversation_history)} messages"
    
    async def generate_personalized_suggestions(
        self,
        search_history: List[dict],
        context: Optional[str] = None
    ) -> List[str]:
        """
        Generate personalized search suggestions based on user history
        """
        try:
            # Extract recent searches
            recent_searches = [item.get('query', '') for item in search_history[-5:]]
            
            prompt = f"""
You are a research assistant. Based on the user's search history, suggest relevant follow-up searches.

Recent searches: {', '.join(recent_searches)}

Context: {context or 'No specific context'}

Generate 3-5 personalized search suggestions that would help the user explore related topics or discover new research areas.
Focus on:
1. Related research areas based on their search patterns
2. Emerging topics in their field of interest
3. Specific aspects they might want to explore further
4. Recent developments or trends

Return each suggestion on a new line, starting with "- ".
"""
            
            response = await self.conversation(
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response:
                return [
                    "What are the latest developments in machine learning?",
                    "Show me papers about transformer models",
                    "Find research on computer vision applications"
                ]
            
            # Parse suggestions
            suggestions = []
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    suggestions.append(line[2:])
                elif line and len(suggestions) < 5:
                    suggestions.append(line)
            
            return suggestions[:5]
            
        except Exception as e:
            logger.error(f"Error generating personalized suggestions: {e}")
            return [
                "What are the latest developments in machine learning?",
                "Show me papers about transformer models",
                "Find research on computer vision applications"
            ]
    


# Create global LLM service instance
conv_llm_service = ConvLLMService()