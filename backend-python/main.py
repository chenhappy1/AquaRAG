from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pathlib import Path
from typing import Any
from bs4 import BeautifulSoup
from docx import Document
from PyPDF2 import PdfReader
from pinecone import Pinecone
import boto3
import shutil
import os

app = FastAPI()

# 允许你的 Angular 前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------
#  Pinecone 初始化
# ---------------------------
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

# ---------------------------
#  AWS S3 初始化
# ---------------------------
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

S3_BUCKET = os.getenv("AWS_S3_BUCKET")


# ---------------------------
#  上传文档 → S3 → 分块 → Pinecone
# ---------------------------
@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    # 上传到 S3
    s3_key = f"uploads/{file.filename}"
    s3.upload_fileobj(file.file, S3_BUCKET, s3_key)

    # 重新读取文件内容用于文本提取
    file.file.seek(0)
    temp_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 提取文本
    try:
        text = extract_text_from_file(temp_path)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    # 分块
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_text(text)

    # 推送到 Pinecone（托管向量化）
    pinecone_records = []
    for idx, chunk in enumerate(chunks):
        pinecone_records.append({
            "id": f"{file.filename}_chunk_{idx+1}",
            "metadata": {
                "text": chunk,
                "source": file.filename,
                "s3_key": s3_key,
                "chunk_index": idx + 1
            }
        })

    index.upsert(vectors=pinecone_records)

    return {
        "status": "success",
        "filename": file.filename,
        "s3_key": s3_key,
        "message": f"Uploaded to S3 and saved {len(chunks)} chunks to Pinecone!"
    }


# ---------------------------
#  文档文本提取
# ---------------------------
def extract_text_from_file(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix in {".txt", ".md", ".csv", ".json"}:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    if suffix == ".pdf":
        reader = PdfReader(file_path)
        return "\n\n".join([page.extract_text() or "" for page in reader.pages])

    if suffix == ".docx":
        document = Document(file_path)
        return "\n\n".join([paragraph.text for paragraph in document.paragraphs if paragraph.text])

    if suffix in {".html", ".htm"}:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, "html.parser")
            return soup.get_text(separator="\n")

    raise ValueError(
        f"Unsupported file type: {suffix}. Supported formats are TXT, PDF, DOCX, HTML."
    )


# ---------------------------
#  构建 Prompt
# ---------------------------
def build_prompt(question: str, docs: list[Any]) -> str:
    if docs:
        context = "\n\n".join([doc["page_content"] for doc in docs])
    else:
        context = ""

    return (
        "You are a helpful assistant. Use the provided document excerpts to answer the question. "
        "If the answer is not contained in the excerpts, say you do not know.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer concisely and cite any source references if available."
    )


# ---------------------------
#  Chat 接口 → Pinecone → DeepSeek
# ---------------------------
@app.post("/api/chat")
async def chat(request: Request):
    payload = await request.json()
    question = payload.get("question", "").strip()
    if not question:
        return {"error": "Question is required."}

    # Pinecone 托管向量化查询
    result = index.query(
        vector=[],
        inputs=[question],
        top_k=3,
        include_metadata=True
    )

    if not result.matches:
        return {"answer": "No matching content found.", "citations": []}

    docs = []
    for match in result.matches:
        docs.append({
            "page_content": match.metadata["text"],
            "metadata": match.metadata
        })

    prompt = build_prompt(question, docs)

    # DeepSeek 回答
    llm = OpenAI(model="DeepSeek-V3", temperature=0.2, max_tokens=512)
    answer = llm.predict(prompt)

    citations = []
    for match in result.matches:
        citations.append({
            "source": match.metadata["source"],
            "snippet": match.metadata["text"][:200],
            "anchor": f"{match.metadata['source']}_chunk_{match.metadata['chunk_index']}"
        })

    return {
        "answer": answer,
        "citations": citations,
    }
