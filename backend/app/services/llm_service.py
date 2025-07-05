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


DAILY_LIMIT = int(os.getenv("LLM_CALLS_PER_DAY", "2000"))
HOURLY_LIMIT = int(os.getenv("LLM_CALLS_PER_HOUR", "500"))
logger = logging.getLogger(__name__)


class LLMService:
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

    def get_embeddings(
        self,
        texts: List[str]
    ) -> Optional[List[List[float]]]:
        if not texts:
            return []
            
        try:
            batch_size = self.BATCH_SIZE 
            total_texts = len(texts)
            total_batches = (total_texts + batch_size - 1) // batch_size
            
            logger.info(f"Starting embedding generation for {total_texts} texts in {total_batches} batches (batch_size={batch_size})")

            all_embeddings = []
            
            # Process batches serially
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_idx = i // batch_size
                
                logger.info(f"Processing batch {batch_idx + 1}/{total_batches} with {len(batch)} texts")
                batch_embeddings = self._sync_embed(batch)
                all_embeddings.append(batch_embeddings)
                logger.info(f"Completed batch {batch_idx + 1}/{total_batches}")

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
            logger.info(f"inputs is ok")
            outputs = self.specter_model(**inputs)
                # Specter-2 把 CLS 位置池化到 pooler_output
            logger.info(f"outputs is ok")
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

# Create global LLM service instance
llm_service = LLMService()