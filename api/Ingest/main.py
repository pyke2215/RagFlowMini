from fastapi import FastAPI, File, UploadFile, Form
from fastapi import HTTPException
import os
import uuid
from fastapi.responses import JSONResponse
from .utils.tokenizer import extract_text_from_pdf, extract_text_from_csv, chunk_text, extract_cleanCSV_sentence, extract_text_from_txt
from services.embedding_service import get_embedding_service
import chromadb
from dotenv import load_dotenv

load_dotenv()


def create_ingest_app() -> FastAPI:
    ingest_app = FastAPI()
    # Dùng EmbeddingService thay vì tự load model
    embedding_service = get_embedding_service()
    chroma_client = chromadb.PersistentClient(path=os.getenv("CHROMADB_PATH", "./chroma_db"))
    @ingest_app.post("/ingest_file")
    async def ingest_file(
        file: UploadFile = File(...),
        collection_name: str = Form("default_collection"),
        clean_csv: bool = Form(False),
    ):
    
        # save file to temporary directory  
        tmp_dir = "./tmp_uploads"
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = os.path.join(tmp_dir, file.filename)
        
        with open(tmp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        
        # Parse file
        file_extension = os.path.splitext(file.filename)[1]
        chunks = []
        if file_extension == ".pdf":
            text = extract_text_from_pdf(tmp_path)
            chunks = chunk_text(text)
        elif file_extension == ".csv":
            if clean_csv:
                chunks = extract_cleanCSV_sentence(tmp_path)
            else:
                chunks = extract_text_from_csv(tmp_path)
        elif file_extension == ".txt":
            chunks = extract_text_from_txt(tmp_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
            
        print("=== DEBUG CHUNKS ===")
        print("file_extension:", file_extension)
        print("type(chunks):", type(chunks))
        print("len(chunks):", len(chunks))
        if chunks:
            print("type(chunks[0]):", type(chunks[0]))
            print("first chunk sample (truncated):", repr(chunks[0][:200]))
            if len(chunks) > 1:
                print("second chunk sample (truncated):", repr(chunks[1][:200]))
        print("===============")
        # Embed chunks sử dụng EmbeddingService
        embeddings_list = []
        try:
            embeddings_numpy = embedding_service.encode(
                chunks, 
                batch_size=64,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            embeddings_list = embeddings_numpy.tolist()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error embedding chunks: {e}")
        collection = chroma_client.get_or_create_collection(name=collection_name)

        ids = [str(uuid.uuid4()) for _ in chunks]

        collection.add(
            documents=chunks,
            embeddings=embeddings_list,
            ids=ids,
            metadatas=[{"source": file.filename} for _ in chunks],
        )
        
        os.remove(tmp_path)


        return {
        "status": "success",
        "embeddings": embeddings_list,
        "collection": collection_name,
        "chunk_count": len(chunks),
        "ids": ids,  
    }
    

    
    @ingest_app.post("/ingest_text")
    async def ingest_text(
        text: str = Form(...),
        collection_name: str = Form("default_collection"),
    ):
        chunks = chunk_text(text)
        # Embed chunks sử dụng EmbeddingService
        embeddings_numpy = embedding_service.encode(
            chunks,
            batch_size=64,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        embeddings_list = embeddings_numpy.tolist()
        collection = chroma_client.get_or_create_collection(name=collection_name)
        ids = [str(uuid.uuid4()) for _ in chunks]
        collection.add(
            documents=chunks,
            embeddings=embeddings_list,
            ids=ids,
            metadatas=[{"source": "text"} for _ in chunks],
        )
        return {
        "status": "success",
        "embeddings": embeddings_list,
        "collection": collection_name,
        "chunk_count": len(chunks),
        "ids": ids,
    }
    
    @ingest_app.delete("/clean_collection")
    async def clean_collection(
        collection_name: str = Form(...),
    ):
        """
        Xóa tất cả documents trong collection ChromaDB.
        Dùng để clean collection trước khi embedding lại, tránh duplicate.
        """
        try:
            # Kiểm tra collection có tồn tại không
            try:
                collection = chroma_client.get_collection(name=collection_name)
                # Đếm số documents trước khi xóa
                count_before = collection.count()
                
                # Lấy tất cả IDs để xóa
                all_data = collection.get()
                if all_data and all_data.get("ids"):
                    collection.delete(ids=all_data["ids"])
                    count_after = collection.count()
                    
                    return {
                        "status": "success",
                        "collection": collection_name,
                        "deleted_count": count_before,
                        "remaining_count": count_after,
                        "message": f"Đã xóa {count_before} documents từ collection '{collection_name}'"
                    }
                else:
                    return {
                        "status": "success",
                        "collection": collection_name,
                        "deleted_count": 0,
                        "remaining_count": 0,
                        "message": f"Collection '{collection_name}' đã trống"
                    }
            except Exception as e:
                # Collection không tồn tại
                return {
                    "status": "error",
                    "collection": collection_name,
                    "message": f"Collection '{collection_name}' không tồn tại: {str(e)}"
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error cleaning collection: {e}")
        
    return ingest_app