from fastapi import FastAPI, UploadFile, File, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Any
from bs4 import BeautifulSoup
from docx import Document
from PyPDF2 import PdfReader
from pinecone import Pinecone
from google import genai
from google.genai import types
from langchain_text_splitters import RecursiveCharacterTextSplitter
import boto3
import shutil
import os
import jwt
from io import BytesIO

# ---------------------------
#  JWT 配置（必须与 Java SECRET 一样）
# ---------------------------
JWT_SECRET = "super-secret-key-change-this-32bytes"

def decode_jwt(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


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
index_name = os.getenv("PINECONE_INDEX_NAME")
index = pc.Index(index_name)

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
@app.post("/api/rag/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    print(">>> upload_document called")
    print("authorization:", authorization)

    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        token = authorization.replace("Bearer ", "")
        claims = decode_jwt(token)
        user_id = claims["sub"]

        # 读取文件内容到内存
        file_bytes = await file.read()
        file_stream = BytesIO(file_bytes)

        # 上传到 S3
        s3_key = f"uploads/{user_id}/{file.filename}"
        print(">>> uploading to S3:", s3_key)
        s3.upload_fileobj(file_stream, S3_BUCKET, s3_key)

        # 保存临时文件
        temp_path = os.path.join(UPLOAD_DIR, file.filename)
        print(">>> saving temp file:", temp_path)
        with open(temp_path, "wb") as buffer:
            buffer.write(file_bytes)

        # 提取文本
        print(">>> extracting text")
        text = extract_text_from_file(temp_path)

        # 分块
        print(">>> splitting text")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = text_splitter.split_text(text)

        # 生成 embedding
        print(">>> generating embeddings")
        client = genai.Client()
        pinecone_records = []

        for idx, chunk in enumerate(chunks):
            embedding = client.models.embed_content(
                model="text-embedding-004",
                contents=chunk
            ).embedding

            pinecone_records.append({
                "id": f"{user_id}_{file.filename}_chunk_{idx+1}",
                "values": embedding,
                "metadata": {
                    "text": chunk,
                    "source": file.filename,
                    "s3_key": s3_key,
                    "chunk_index": idx + 1,
                    "user_id": user_id
                }
            })

        print(">>> upserting to Pinecone")
        index.upsert(namespace=user_id, vectors=pinecone_records)

        print(">>> upload success")
        return {
            "status": "success",
            "filename": file.filename,
            "s3_key": s3_key,
            "message": f"Uploaded to S3 and saved {len(chunks)} chunks to Pinecone!"
        }

    except Exception as e:
        print(">>> ERROR:", e)
        raise e



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
#  Chat 接口 → Pinecone → Gemini
# ---------------------------
@app.post("/api/rag/chat")
async def chat(request: Request, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "")
    claims = decode_jwt(token)
    user_id = claims["sub"]

    payload = await request.json()
    question = payload.get("question", "").strip()

    if not question:
        return {"error": "Question is required."}

    # Pinecone 查询
    result = index.query(
        namespace=user_id,
        top_k=3,
        include_metadata=True,
        query={"text": question}
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

    client = genai.Client()

    resp = client.models.generate_content(
        model="gemini-3.1-flash-lite",
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)