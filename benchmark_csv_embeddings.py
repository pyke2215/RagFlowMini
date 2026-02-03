import time
from api.Ingest.utils.tokenizer import extract_text_from_csv, chunk_text
from sentence_transformers import SentenceTransformer
import os
import torch
# Đường dẫn tới file CSV cần test
CSV_PATH = r"E:\Phat\AI\LLM\Embeddings\api\Ingest\data\BooksDatasetClean.csv"

def main():
    print(torch.cuda.is_available(), torch.cuda.get_device_name(0))
    print("Loading model...")
    t0 = time.perf_counter()
    model = SentenceTransformer("BAAI/bge-m3")
    model.to(torch.device("cuda"))
    t1 = time.perf_counter()
    print(f"Model loaded in {t1 - t0:.2f} s")

    print("Reading & converting CSV to text chunks...")
    t2 = time.perf_counter()
    # extract_text_from_csv của bạn đang trả về list[str] (mỗi row là 1 text)
    rows_as_text = extract_text_from_csv(CSV_PATH)  # list[str]
    # Nếu muốn chunk thêm từng row thì lặp, ở đây mình coi mỗi row là 1 chunk luôn:
    chunks = chunk_text(rows_as_text, chunk_size=500, chunk_overlap=50)
    t3 = time.perf_counter()
    print(f"CSV processed, {len(chunks)} chunks, in {t3 - t2:.2f} s")

    print("Embedding...")
    t4 = time.perf_counter()
    embeddings = []
    try:
        for chunk in chunks:
            embedding = model.encode(chunk, batch_size=16, show_progress_bar=True, convert_to_numpy=True)
            embeddings.append(embedding)
    except Exception as e:
        print(f"Error embedding: {e}")
        return
    t5 = time.perf_counter()
    print(f"Embedding done in {t5 - t4:.2f} s")

    total = t5 - t0
    print(f"\nTotal time: {total:.2f} s (~{total/60:.2f} min)")
    print(f"Num chunks: {len(chunks)}, embedding dim: {embeddings.shape[1]}")

if __name__ == "__main__":
    main()