# services/llm_service.py
import os
from functools import lru_cache
from dotenv import load_dotenv
from typing import List, Dict, Optional
from openai import OpenAI, AsyncOpenAI
import time
load_dotenv()


class LLMService:
    """
    Service để quản lý LLM client (OpenAI, Ollama, etc.)
    Cấu hình từ .env, không cần truyền tham số.
    """

    def __init__(self):
        """
        Load LLM client từ .env.
        """
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        self.model_name = os.getenv("LLM_MODEL", "llama3.2")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.base_url = os.getenv("LLM_BASE_URL", None)
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))
        
        if self.provider == "ollama":
            self.base_url = self.base_url or "http://localhost:11434/v1"
            if self.base_url and not self.base_url.endswith("/v1"):
                if self.base_url.endswith("/"):
                    self.base_url = self.base_url + "v1"
                else:
                    self.base_url = self.base_url + "/v1"
            self.api_key = "ollama"
            self.client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=300.0
            )
            print(f"  Note: Ollama API compatible mode - make sure Ollama is running on {self.base_url}")
        else:
            if not self.api_key:
                raise ValueError("LLM_API_KEY is required for OpenAI provider")
            self.base_url = self.base_url or "https://api.openai.com/v1"
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        print(self.client)
        print(f"LLM Service initialized:")
        print(f"  Provider: {self.provider}")
        print(f"  Model: {self.model_name}")
        print(f"  Base URL: {self.base_url}")
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate response từ messages.
        
        Args:
            messages: List of message dicts với format:
                [{"role": "system", "content": "..."},
                 {"role": "user", "content": "..."},
                 {"role": "assistant", "content": "..."}]
            temperature: Override temperature (optional)
            max_tokens: Override max_tokens (optional)
        
        Returns:
            Generated response string
        """
        try:
            print(f"[LLM] Generating with model: {self.model_name}")
            print(f"[LLM] Messages count: {len(messages)}")
            
            # Calculate total input size
            total_chars = sum(len(msg.get("content", "")) for msg in messages)
            est_tokens = total_chars // 4  # Rough estimate
            print(f"[LLM] Total input: ~{total_chars} chars (~{est_tokens} tokens)")
            print(f"[LLM] Max tokens: {max_tokens or self.max_tokens}")
            print(f"[LLM] Temperature: {temperature or self.temperature}")
            
            request_start = time.perf_counter()
            print(f"[LLM] Sending request to {self.base_url} at {time.strftime('%H:%M:%S')}")
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens
            )
            
            request_time = (time.perf_counter() - request_start) * 1000
            result = response.choices[0].message.content
            
            if hasattr(response, 'usage'):
                usage = response.usage
                print(f"[LLM] Token usage:")
                print(f"  - Prompt tokens: {usage.prompt_tokens if hasattr(usage, 'prompt_tokens') else 'N/A'}")
                print(f"  - Completion tokens: {usage.completion_tokens if hasattr(usage, 'completion_tokens') else 'N/A'}")
                print(f"  - Total tokens: {usage.total_tokens if hasattr(usage, 'total_tokens') else 'N/A'}")
            
            print(f"[LLM] Request time: {request_time:.2f}ms")
            print(f"[LLM] Generation successful, response length: {len(result)} chars")
            return result
        except Exception as e:
            print(f"[LLM] Generation error details: {type(e).__name__}: {str(e)}")
            raise Exception(f"LLM generation error: {str(e)}")
    
    async def generate_from_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate response từ prompt đơn giản (legacy format).
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt (có thể chứa context)
            conversation_history: Optional conversation history
            temperature: Override temperature
            max_tokens: Override max_tokens
        
        Returns:
            Generated response string
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": user_prompt})
        
        return await self.generate(messages, temperature, max_tokens)


_llm_service_instance = None

@lru_cache(maxsize=1)
def get_llm_service() -> Optional[LLMService]:
    """
    Singleton factory cho LLMService.
    Nếu không có cấu hình LLM, trả về None (sẽ dùng fallback).
    """
    global _llm_service_instance
    if _llm_service_instance is None:
        try:
            provider = os.getenv("LLM_PROVIDER", "ollama").lower()
            has_api_key = bool(os.getenv("LLM_API_KEY", ""))
            
            if os.getenv("LLM_PROVIDER") or has_api_key or provider == "ollama":
                print(f"[LLM Service] Initializing with provider: {provider}")
                _llm_service_instance = LLMService()
                print(f"[LLM Service] Initialization successful")
            else:
                print("LLM Service: No configuration found, using fallback mode")
                return None
        except Exception as e:
            print(f"LLM Service initialization failed: {e}")
            import traceback
            traceback.print_exc()
            print("Falling back to context-only responses")
            return None
    return _llm_service_instance

