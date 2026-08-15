from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Any
from bs4 import BeautifulSoup
from docx import Document
from PyPDF2 import PdfReader
from pinecone import Pinecone
from google import genai
from google.genai import types
import boto3
import shutil
import os

app = FastAPI()

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
#  Pinecone 初始化（托管 embedding）
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
async def upload_document(request: Request, file: UploadFile = File(...)):
    payload = await request.form()
    user_id = payload.get("user_id")

    if not user_id:
        return {"status": "error", "message": "user_id is required"}

    s3_key = f"uploads/{user_id}/{file.filename}"
    s3.upload_fileobj(file.file, S3_BUCKET, s3_key)

    file.file.seek(0)
    temp_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        text = extract_text_from_file(temp_path)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_text(text)

    pinecone_records = []
    for idx, chunk in enumerate(chunks):
        pinecone_records.append({
            "id": f"{user_id}_{file.filename}_chunk_{idx+1}",
            "values": None,  # 托管 embedding
            "metadata": {
                "text": chunk,
                "source": file.filename,
                "s3_key": s3_key,
                "chunk_index": idx + 1,
                "user_id": user_id
            }
        })

    index.upsert(vectors=pinecone_records, namespace=user_id)

    return {
        "status": "success",
        "filename": file.filename,
        "s3_key": s3_key,
        "message": f"Uploaded to S3 and saved {len(chunks)} chunks to Pinecone!"
    }


# ---------------------------
#  文本提取
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

    raise ValueError(f"Unsupported file type: {suffix}")


# ---------------------------
#  Chat 接口 → Pinecone → Gemini 3 Flash Preview
# ---------------------------
@app.post("/api/chat")
async def chat(request: Request):
    payload = await request.json()
    question = payload.get("question", "").strip()
    user_id = payload.get("user_id")

    if not question:
        return {"error": "Question is required."}
    if not user_id:
        return {"error": "user_id is required."}

    result = index.query(
        namespace=user_id,
        queries=[{"text": question}],
        top_k=3,
        include_metadata=True
    )

    if not result.matches:
        return {"answer": "No matching content found.", "citations": []}

    docs = [{"page_content": m.metadata["text"], "metadata": m.metadata} for m in result.matches]

    context = "\n\n".join([d["page_content"] for d in docs])
    prompt = (
        "You are a helpful assistant. Use the provided document excerpts to answer the question.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer concisely."
    )

    # ---------------------------
    #  Gemini 3 Flash Preview 调用
    # ---------------------------
    client = genai.Client()

    resp = client.models.generate_content(
        model="Gemini 2.5 Flash Lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            top_p=0.95,
            thinking_config=types.ThinkingConfig(thinking_budget=2048)
        )
    )

    answer = resp.text

    citations = [{
        "source": m.metadata["source"],
        "snippet": m.metadata["text"][:200],
        "anchor": f"{m.metadata['source']}_chunk_{m.metadata['chunk_index']}"
    } for m in result.matches]

    return {"answer": answer, "citations": citations}
