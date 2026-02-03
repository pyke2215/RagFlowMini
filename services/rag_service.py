# services/rag_service.py
import chromadb
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from functools import lru_cache
from services.embedding_service import get_embedding_service
from services.llm_service import get_llm_service

load_dotenv()


class RAGService:
    def __init__(self, embedding_service=None, chroma_client=None, llm_service=None):
        if embedding_service is None:
            self.embedding_service = get_embedding_service()
        else:
            self.embedding_service = embedding_service

        if chroma_client is None:
            chroma_path = os.getenv("CHROMADB_PATH", "./chroma_db")
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        else:
            self.chroma_client = chroma_client

        if llm_service is None:
            self.llm_service = get_llm_service()
        else:
            self.llm_service = llm_service

    async def retrieve_context(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        redis_cache=None,
    ) -> List[Dict]:
        import time

        cached_embedding = None
        if redis_cache:
            try:
                cached_embedding_data = redis_cache.get(f"embed:query:{hash(query)}")
                if cached_embedding_data:
                    import json
                    cached_embedding = json.loads(cached_embedding_data)
                    print(f"[RAG] Using cached query embedding")
            except Exception as e:
                print(f"[RAG] Cache check error: {e}")

        t0 = time.perf_counter()
        if cached_embedding:
            import numpy as np
            query_embedding = np.array(cached_embedding)
        else:
            query_embedding = self.embedding_service.encode_single(
                query, convert_to_numpy=True
            )
            if redis_cache:
                try:
                    redis_cache.cache_query_embedding(query, query_embedding.tolist())
                except Exception as e:
                    print(f"[RAG] Cache save error: {e}")
        embed_time = (time.perf_counter() - t0) * 1000
        print(f"[RAG] Query embedding took: {embed_time:.2f}ms")

        t0 = time.perf_counter()
        collection = self.chroma_client.get_collection(collection_name)
        results = collection.query(
            query_embeddings=[query_embedding.tolist()], n_results=top_k
        )
        retrieval_time = (time.perf_counter() - t0) * 1000
        print(f"[RAG] ChromaDB retrieval took: {retrieval_time:.2f}ms")

        contexts = []
        for i, doc in enumerate(results["documents"][0]):
            contexts.append(
                {
                    "content": doc,
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
            )

        return contexts

    async def decide_and_generate(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        redis_cache=None,
        previous_queries: List[str] = None,
    ) -> Dict[str, object]:
        """
        Bước điều phối thông minh:
        1. Hỏi LLM xem query có cần dùng context từ knowledge base sách không
           và query có liên quan đến sách không.
        2. Nếu cần và có liên quan: retrieve context từ Chroma rồi generate final response.
        3. Nếu không: bỏ qua bước retrieve và generate response chỉ dựa trên query.

        Trả về dict bao gồm:
            - response: câu trả lời cuối cùng
            - used_context: bool (có dùng context hay không)
            - contexts: list context thực sự đã dùng (có thể rỗng)
        """
        print("[RAG] Running decide_and_generate flow")

        # Nếu không có LLM service thì fallback như cũ với context
        if not self.llm_service:
            print("[RAG] No LLM service, falling back to retrieve_context + _fallback_response")
            contexts = await self.retrieve_context(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                redis_cache=redis_cache,
            )
            context_text = "\n\n".join(
                [f"[{i+1}] {ctx['content']}" for i, ctx in enumerate(contexts)]
            )
            response = self._fallback_response(context_text, query)
            return {
                "response": response,
                "used_context": True,
                "contexts": contexts,
            }

        # 1) Hỏi LLM xem có cần context không và có liên quan sách không
        classification_system = (
            "You are a classifier that decides how to route a user query.\n"
            "- The knowledge base ONLY contains data about books.\n"
            "- Your task is to answer STRICTLY in JSON with the following keys:\n"
            '  {\n'
            '    "needs_context": true/false,\n'
            '    "is_book_related": true/false,\n'
            '    "reason": "short explanation in Vietnamese"\n'
            "  }\n"
            "- Do not add any extra text outside the JSON.\n"
        )
        classification_user = (
            "User query:\n"
            f"{query}\n\n"
            "Hãy phân tích xem:\n"
            "1) Câu hỏi này có LIÊN QUAN đến sách / nội dung sách không?\n"
            "2) Có CẦN sử dụng kiến thức chi tiết từ kho sách (knowledge base) để trả lời tốt không?\n"
        )

        classification_messages = [
            {"role": "system", "content": classification_system},
            {"role": "user", "content": classification_user},
        ]

        print("[RAG] Calling LLM for classification (needs_context + is_book_related)")
        raw_clf = await self.llm_service.generate(
            messages=classification_messages,
            temperature=0.0,
            max_tokens=256,
        )
        print(f"[RAG] Classification raw output: {raw_clf}")

        import json

        needs_context = True
        is_book_related = True
        try:
            clf_data = json.loads(raw_clf)
            needs_context = bool(clf_data.get("needs_context", True))
            is_book_related = bool(clf_data.get("is_book_related", True))
        except Exception as e:
            print(f"[RAG] Failed to parse classification JSON, fallback to using context. Error: {e}")

        # 2) Quyết định có retrieve context hay không
        contexts: List[Dict] = []
        if needs_context and is_book_related:
            print("[RAG] Classifier decided to USE context from knowledge base")
            contexts = await self.retrieve_context(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                redis_cache=redis_cache,
            )
        else:
            print(
                f"[RAG] Classifier decided to SKIP context. needs_context={needs_context}, "
                f"is_book_related={is_book_related}"
            )

        # 3) Generate final response (có thể có hoặc không context)
        result = await self.generate_response(
            query=query,
            contexts=contexts,
            previous_queries=previous_queries if previous_queries != None and len(previous_queries) > 0 else [],
        )
    
        return {
            "response": result.get("response", ""),
            "options": result.get("options", []),
            "used_context": len(contexts) > 0,
            "contexts": contexts,
            "needs_context": needs_context,
            "is_book_related": is_book_related,
        }

    def build_prompt(
        self,
        context_text: str,
        query: str = "",
        is_require_more_option: bool = True,
        previous_queries: List[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Build prompt messages cho LLM từ context, query và conversation history.

        Returns:
            List of message dicts với format OpenAI API:
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        system_prompt = """You are a helpful AI assistant that answers questions based on the provided context.
- The knowledge base ONLY contains information about books (titles, authors, descriptions, ratings, etc.).
- Use the context information to provide accurate and relevant answers about books.
- If the user asks about something that is clearly outside the domain of books (e.g., programming, travel, cooking) and the context does not contain relevant information, say that this knowledge base only contains book data and you cannot answer from it.
- In that case, you may answer briefly from your general knowledge, but make it clear that the answer is not based on the provided context.
- If the context doesn't contain enough information even for book‑related questions, say so clearly and suggest the user provide more details (e.g., genre, topic, audience).
- Be conversational and natural in your responses.
- The context may be noisy or hard for humans to read, so rewrite and summarize it clearly.
- Your tone must be polite, friendly, and helpful.
- If the user query is just casual conversation or simple researching and does not require deep analysis, you may ignore the context and answer directly.
- IMPORTANT: You MUST always structure your answer using the exact sections provided in the user message:
  - First section: '========Main Response========'
  - Second section (if requested): '========More Option========'
- Do not add extra top‑level sections outside of these. You can only write content under those section headers."""
        
        user_prompt_parts = []
        
        # Thêm previous queries vào context nếu có (chỉ từ câu hỏi thứ 2 trở đi)
        previous_context = ""
        if previous_queries and len(previous_queries) > 0:
            previous_context = "\n\nPrevious questions from this conversation (for context only, do not answer them):\n"
            for i, prev_q in enumerate(previous_queries, 1):
                previous_context += f"{i}. {prev_q}\n"
        
        user_query = f"\nQuery from user: {query}"
        
        # Phần hướng dẫn chung
        intro_text = "You will receive a user query"
        if context_text.strip():
            intro_text += " and related context from a knowledge base"
        intro_text += ".\nUse them to answer the question in Vietnamese.\n\n"
        
        # Phần context từ knowledge base (nếu có)
        context_section = ""
        if context_text.strip():
            context_section = f"\nContext from knowledge base:\n{context_text}\n"
        
        user_prompt_parts.append(
            intro_text
            + previous_context
            + "Here is the current query"
            + (" and context:" if context_text.strip() else ":")
            + user_query
            + context_section
        )

        # Template phần trả lời chính
        user_prompt_parts.append(
            "========Main Response========\n"
            "Hãy viết câu trả lời chính, rõ ràng, súc tích, dễ hiểu cho người dùng.\n"
            "- Nếu câu hỏi là tìm sách / gợi ý sản phẩm, hãy nêu 1–3 lựa chọn tốt nhất và giải thích ngắn gọn vì sao.\n"
            "- Nếu thông tin trong context không đủ, hãy nói rõ là không đủ dữ liệu và gợi ý người dùng cung cấp thêm.\n"
        )

        # Template phần gợi ý tương tác thêm (options cho bước chat tiếp theo)
        if is_require_more_option:
            user_prompt_parts.append(
                "========More Option========\n"
                "Đưa ra 3–5 gợi ý dưới dạng câu hỏi hoặc yêu cầu mà người dùng có thể hỏi tiếp.\n"
                "Mỗi gợi ý phải là một câu hỏi/yêu cầu hoàn chỉnh, có thể dùng làm button để chat tiếp.\n"
                "Trả lời theo dạng bullet, mỗi dòng là một câu hỏi/yêu cầu, ví dụ:\n"
                "- Hỏi về sách lịch sử cùng chủ đề nhưng dành cho người mới bắt đầu\n"
                "- Hỏi gợi ý sách nâng cao hơn cho người đã có kiến thức nền\n"
                "- Yêu cầu tóm tắt nhanh nội dung chính của cuốn sách vừa được gợi ý\n"
                "Lưu ý: Mỗi gợi ý phải là một câu hoàn chỉnh, không cần dấu gạch đầu dòng trong nội dung.\n"
            )
        
        user_prompt = "\n\n".join(user_prompt_parts)
        print("user prompt: ", user_prompt)
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def _parse_response(self, raw_response: str) -> Dict[str, object]:
        """
        Parse response từ LLM để tách Main Response và More Option.
        
        Returns:
            Dict với keys:
                - response: str (chỉ nội dung Main Response, không có header)
                - options: List[str] (mảng các options, mỗi option là một câu hỏi/yêu cầu)
        """
        import re
        
        # Tách phần Main Response (hỗ trợ cả = và - trong marker)
        # Pattern: ========Main Response======== hoặc ========Main Response--------
        main_response_match = re.search(
            r'========Main Response[=-]+\s*(.*?)(?=\s*========More Option[=-]+|$)',
            raw_response,
            re.DOTALL | re.IGNORECASE
        )
        
        # Tách phần More Option (hỗ trợ cả = và - trong marker)
        more_option_match = re.search(
            r'========More Option[=-]+\s*(.*?)$',
            raw_response,
            re.DOTALL | re.IGNORECASE
        )
        
        # Extract Main Response
        if main_response_match:
            main_response = main_response_match.group(1).strip()
        else:
            # Nếu không tìm thấy header, lấy toàn bộ response trước phần More Option (fallback)
            if more_option_match:
                # Nếu có More Option nhưng không có Main Response header, lấy phần trước More Option
                main_response = raw_response[:more_option_match.start()].strip()
            else:
                # Không có cả 2 headers, lấy toàn bộ response
                main_response = raw_response.strip()
        
        # Đảm bảo loại bỏ hoàn toàn marker nếu còn sót lại (phòng trường hợp LLM trả về không đúng format)
        # Loại bỏ bất kỳ marker nào ở đầu response
        main_response = re.sub(r'^========Main Response[=-]+\s*', '', main_response, flags=re.IGNORECASE).strip()
        
        # Extract Options
        options = []
        if more_option_match:
            options_text = more_option_match.group(1).strip()
            # Parse từng dòng, bỏ qua dòng trống
            for line in options_text.split('\n'):
                line = line.strip()
                if line:
                    # Loại bỏ dấu gạch đầu dòng nếu có (-, *, •, số thứ tự, etc.)
                    # Pattern: bỏ qua các ký tự đầu dòng như -, *, •, số., chữ số.
                    line = re.sub(r'^[-*•]\s*', '', line)  # Bỏ dấu gạch đầu dòng
                    line = re.sub(r'^\d+[.)]\s*', '', line)  # Bỏ số thứ tự (1. 2. 3.)
                    if line:  # Chỉ thêm nếu còn nội dung sau khi loại bỏ
                        options.append(line)
        
        return {
            "response": main_response,
            "options": options
        }

    async def generate_response(
        self,
        query: str,
        contexts: List[Dict],
        system_prompt: str = None,
        previous_queries: List[str] = None,
    ) -> Dict[str, object]:
        """
        Generate response từ query, contexts và conversation history.
        Sử dụng LLM nếu có, nếu không thì fallback về context-only.
        """
        context_text = "\n\n".join(
            [f"[{i+1}] {ctx['content']}" for i, ctx in enumerate(contexts)]
        )
        print(f"[RAG] Context for building prompt: {len(contexts)} contexts")

        if self.llm_service:
            print(f"[RAG] Using LLM service: {type(self.llm_service).__name__}")
            try:
                messages = self.build_prompt(
                    context_text=context_text,
                    query=query,
                    is_require_more_option=True,
                    previous_queries=previous_queries or [],
                )     
                print("\n" + "=" * 80)
                print("[RAG] ===== LLM INPUT DEBUG =====")
                print("=" * 80)
                print(f"[RAG] Total messages: {len(messages)}")
                print(f"[RAG] Contexts count: {len(contexts)}")
                print("\n--- Messages to LLM ---")
                for i, msg in enumerate(messages):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    print(f"  [{i+1}] {role}: {len(content)} chars")
                    if role == "system":
                        print(f"      Preview: {content[:200]}...")
                    else:
                        print(f"      Preview: {content[:500]}...")
                print("\n--- Query and Context Summary ---")
                print(f"Query length: {len(query)} chars")
                print(f"Context text length: {len(context_text)} chars")
                print(f"Number of contexts: {len(contexts)}")
                print(f"\nQuery: {query}")
                print(f"\nContext preview (first 500 chars):\n{context_text[:500]}...")

                print(f"[RAG] Calling LLM with {len(messages)} messages")
                raw_response = await self.llm_service.generate(
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1024
                )
                print(f"[RAG] LLM raw response received, length: {len(raw_response)}")
                
                # Parse response để tách Main Response và Options
                parsed = self._parse_response(raw_response)
                print(f"[RAG] Parsed response: {len(parsed['response'])} chars, {len(parsed['options'])} options")
                return parsed
            except Exception as e:
                print(f"[RAG] LLM generation error: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                context_text = "\n\n".join([f"[{i+1}] {ctx['content']}" for i, ctx in enumerate(contexts)])
                fallback_text = self._fallback_response(context_text, query)
                return {
                    "response": fallback_text,
                    "options": []
                }
        else:
            print(f"[RAG] No LLM service available, using fallback")
            context_text = "\n\n".join([f"[{i+1}] {ctx['content']}" for i, ctx in enumerate(contexts)])
            fallback_text = self._fallback_response(context_text, query)
            return {
                "response": fallback_text,
                "options": []
            }

    def _fallback_response(self, context_text: str, query: str) -> str:
        """Fallback response khi không có LLM"""
        return f"""Based on the available context, here is relevant information:

{context_text[:1000]}

Note: This is a summary of retrieved documents. For more natural responses, please configure an LLM service (OpenAI, Ollama, etc.) in your .env file."""


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    """
    FastAPI dependency factory that returns a singleton RAGService instance.
    """

    return RAGService()
