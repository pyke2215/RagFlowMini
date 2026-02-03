import csv
import re
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
import chardet
def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file and normalize Vietnamese text"""
    reader = PdfReader(file_path)
    texts = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        normalized_text = normalize_text_vi(page_text)
        texts.append(normalized_text)
    return "\n\n".join(texts)

def extract_text_from_csv(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        reader = csv.reader(file)
        rows = list(reader)
        if not rows or len(rows) < 2:
            return []
        
        # Hàng 1: Tên nhóm thông tin (có thể có merged cells → lặp lại)
        group_row = rows[0]
        # Hàng 2: Headers
        headers = rows[1]
        
        # Map mỗi header với nhóm của nó
        # Ví dụ: {"Tên sách": "Thông tin cơ bản", "Mô tả nhanh": "Mô tả", ...}
        header_to_group = {}
        current_group = ""
        
        for i, header in enumerate(headers):
            # Nếu có tên nhóm ở vị trí này (không rỗng và khác nhóm hiện tại)
            if i < len(group_row) and group_row[i].strip():
                current_group = group_row[i].strip()
            # Map header với nhóm hiện tại
            if header.strip():
                header_to_group[header.strip()] = current_group
        
        # Nhóm các header theo tên nhóm
        group_to_headers = {}
        for header, group in header_to_group.items():
            if group not in group_to_headers:
                group_to_headers[group] = []
            group_to_headers[group].append(header)
        
        chunks = []
        
        # Xử lý từng row dữ liệu (từ hàng 3 trở đi)
        for row in rows[2:]:
            # Tạo chunk cho mỗi nhóm thông tin
            for group_name, group_headers in group_to_headers.items():
                chunk_text = ""
                for header in group_headers:
                    if header in headers:
                        idx = headers.index(header)
                        value = row[idx] if idx < len(row) else ""
                        if value and value.strip():  # Chỉ thêm field có giá trị
                            chunk_text += f"{header}: {value}\n"
                
                if chunk_text.strip():
                    normalized = normalize_text_vi(chunk_text.strip())
                    chunks.append(normalized)
        
        return chunks

def extract_cleanCSV_sentence(file_path: str) -> list[str]:
    # detect encoding
    with open(file_path, "rb") as f:
        raw = f.read(20000)
        print("raw: ", raw)
    encoding = chardet.detect(raw)["encoding"]
    # print("Detected encoding:", encoding)

    chunks = []
    with open(file_path, "r", encoding=encoding) as file:
        reader = csv.reader(file)
        next(reader, None)  # bỏ header

        for row in reader:
            if not row:
                continue
            text = normalize_text_vi(row[0].strip())
            chunks.append(text)

    return chunks

def extract_text_from_txt(file_path: str) -> list[str]:
    """
    Extract text from a text file where each line is a sentence describing a book.
    Each line becomes one chunk in the returned array.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        List of strings, where each string is a normalized sentence (one line from the file)
    """
    # Detect encoding
    with open(file_path, "rb") as f:
        raw = f.read(20000)
    encoding = chardet.detect(raw)["encoding"]
    print(f"[Tokenizer] Detected encoding for {file_path}: {encoding}")
    
    chunks = []
    try:
        with open(file_path, "r", encoding=encoding, errors="ignore") as file:
            for line in file:
                # Strip whitespace and skip empty lines
                line = line.strip()
                if line:
                    # Normalize Vietnamese text
                    normalized_text = normalize_text_vi(line)
                    chunks.append(normalized_text)
    except Exception as e:
        print(f"[Tokenizer] Error reading file {file_path}: {e}")
        # Fallback to utf-8 if detected encoding fails
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                for line in file:
                    line = line.strip()
                    if line:
                        normalized_text = normalize_text_vi(line)
                        chunks.append(normalized_text)
        except Exception as e2:
            print(f"[Tokenizer] Fallback encoding also failed: {e2}")
            return []
    
    print(f"[Tokenizer] Extracted {len(chunks)} sentences from {file_path}")
    return chunks
def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    if not text.strip():
        return []
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", ""]
    )
    return splitter.split_text(text)


def normalize_text_vi(text: str) -> str:
    if not text:
        return text
    
    # 1. Thêm khoảng trắng sau dấu câu nếu thiếu (trước chữ/số)
    # Pattern: dấu câu + chữ/số (không có khoảng trắng) → dấu câu + khoảng trắng + chữ/số
    text = re.sub(r'([,.!?:;])([^\s\d])', r'\1 \2', text)
    
    # 2. Thêm khoảng trắng giữa chữ và số: "Năm2002" → "Năm 2002"
    # Pattern: chữ cái tiếng Việt + số → chữ + khoảng trắng + số
    text = re.sub(r'([a-zA-ZàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ])(\d)', r'\1 \2', text)
    
    # 3. Thêm khoảng trắng giữa số và chữ: "2002Việt" → "2002 Việt"
    # Pattern: số + chữ cái → số + khoảng trắng + chữ
    text = re.sub(r'(\d)([a-zA-ZàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ])', r'\1 \2', text)
    
    # 4. Thêm khoảng trắng sau dấu phẩy/chấm nếu thiếu (trước số)
    # Pattern: dấu câu + số (không có khoảng trắng) → dấu câu + khoảng trắng + số
    text = re.sub(r'([,.!?:;])(\d)', r'\1 \2', text)
    
    # 5. Xử lý trường hợp đặc biệt: dấu phẩy/chấm giữa số (giữ nguyên)
    # Ví dụ: "1,234" hoặc "3.14" không nên thành "1, 234" hoặc "3. 14"
    # Pattern: số + dấu phẩy/chấm + số → giữ nguyên (không thêm khoảng trắng)
    # (Đã được xử lý tự nhiên bởi các regex trên)
    
    # 6. Loại bỏ khoảng trắng thừa (nhiều khoảng trắng liên tiếp → 1 khoảng trắng)
    text = re.sub(r'\s+', ' ', text)
    
    # 7. Loại bỏ khoảng trắng ở đầu/cuối
    text = text.strip()
    
    return text