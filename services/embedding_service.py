# services/embedding_service.py
from sentence_transformers import SentenceTransformer
import torch
import os
from functools import lru_cache
from dotenv import load_dotenv
from typing import List, Union
import numpy as np

load_dotenv()


class EmbeddingService:
    """
    Service để quản lý embedding model.
    Model và device được cấu hình từ .env, không cần truyền tham số.
    Model luôn ở 1 đường dẫn duy nhất, device luôn là cuda.
    """

    def __init__(self):
        """
        Load model và device từ .env.
        Model path và device được set cố định từ cấu hình.
        """
        self.model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
        self.cache_folder = os.getenv("EMBEDDING_CACHE_FOLDER", None)
        self.device = os.getenv("EMBEDDING_DEVICE", "cuda")
        
        print(f"Loading embedding model: {self.model_name}")
        print(f"Cache folder: {self.cache_folder or 'default (~/.cache/huggingface/)'}")
        print(f"Device: {self.device}")
        
        if self.cache_folder:
            self.model = SentenceTransformer(self.model_name, cache_folder=self.cache_folder)
        else:
            self.model = SentenceTransformer(self.model_name)
        
        if self.model is None:
            raise ValueError("Model failed to load - model is None")
        
        if not hasattr(self.model, '_modules') or len(self.model._modules) == 0:
            raise ValueError("Model loaded but has no modules")
        
        if self.device == "cuda" and torch.cuda.is_available():
            print(f"Model will use GPU: {torch.cuda.get_device_name(0)}")
        else:
            if self.device == "cuda":
                print("Warning: CUDA requested but not available, falling back to CPU")
                self.device = "cpu"
            print("Model will use CPU")
        
        print(f"Embedding model loaded successfully!")
    
    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 64,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
        normalize_embeddings: bool = False
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Encode text(s) thành embeddings.
        
        Args:
            texts: String hoặc list of strings
            batch_size: Batch size cho encoding
            show_progress_bar: Hiển thị progress bar
            convert_to_numpy: Convert về numpy array
            normalize_embeddings: Normalize embeddings về unit vector
        
        Returns:
            Numpy array hoặc list of numpy arrays
        """
        return self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress_bar,
            convert_to_numpy=convert_to_numpy,
            normalize_embeddings=normalize_embeddings,
            device=self.device
        )
    
    def encode_single(self, text: str, **kwargs) -> np.ndarray:
        """Encode một text duy nhất, trả về numpy array 1D"""
        embeddings = self.encode([text], **kwargs)
        return embeddings[0] if isinstance(embeddings, np.ndarray) else embeddings[0]
    
    def get_model_info(self) -> dict:
        """Lấy thông tin về model"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "cache_folder": self.cache_folder,
            "max_seq_length": self.model.max_seq_length if hasattr(self.model, 'max_seq_length') else None,
            "embedding_dimension": self.model.get_sentence_embedding_dimension() if hasattr(self.model, 'get_sentence_embedding_dimension') else None
        }


_embedding_service_instance = None


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """
    Singleton factory cho EmbeddingService với @lru_cache.
    Model và device được load từ .env, không cần truyền tham số.
    """
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance
