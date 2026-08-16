from fastapi import FastAPI, UploadFile, File, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from bs4 import BeautifulSoup
from docx import Document
from PyPDF2 import PdfReader
from pinecone import Pinecone
from google import genai
from google.genai import types
from google.genai import EmbeddingsClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
import boto3
import os
import jwt
from io import BytesIO

# ---------------------------
#  JWT 配置
# ---------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-this-32bytes")

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

# ---------------------------
#  Pinecone 初始化（手动 embedding）
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
#  上传文档 → S3 → 内存提取文本 → 分块 → Gemini embedding → Pinecone
# ---------------------------
@app.post("/api/rag/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    print(">>> upload_document called")

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
    # s3.upload_fileobj(file_stream, S3_BUCKET, s3_key)

    # 从内存提取文本
    print(">>> extracting text from memory")
    text = extract_text_from_memory(file.filename, file_bytes)

    # 分块
    print(">>> splitting text")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_text(text)

    # Gemini embedding（适配 google-genai 2.17.0）
    print(">>> generating embeddings")
    embed_client = EmbeddingsClient()
    pinecone_records = []

    for idx, chunk in enumerate(chunks):
        resp = embed_client.embed(
            model="models/embedding-001",
            content=chunk
        )
        embedding = resp.embedding  # ⭐ 正确取法

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

    return {
        "status": "success",
        "filename": file.filename,
        "s3_key": s3_key,
        "message": f"Uploaded to S3 and saved {len(chunks)} chunks to Pinecone!"
    }


# ---------------------------
#  内存文本提取（不保存本地）
# ---------------------------
def extract_text_from_memory(filename: str, file_bytes: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    stream = BytesIO(file_bytes)

    if suffix in {".txt", ".md", ".csv", ".json"}:
        return file_bytes.decode("utf-8", errors="ignore")

    if suffix == ".pdf":
        reader = PdfReader(stream)
        return "\n\n".join([page.extract_text() or "" for page in reader.pages])

    if suffix == ".docx":
        document = Document(stream)
        return "\n\n".join([p.text for p in document.paragraphs if p.text])

    if suffix in {".html", ".htm"}:
        soup = BeautifulSoup(file_bytes.decode("utf-8", errors="ignore"), "html.parser")
        return soup.get_text(separator="\n")

    raise ValueError(f"Unsupported file type: {suffix}")


# ---------------------------
#  Chat 接口 → Gemini embedding → Pinecone → Gemini 生成答案
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

    # Gemini embedding（适配 google-genai 2.17.0）
    embed_client = EmbeddingsClient()
    resp = embed_client.embed(
        model="models/embedding-001",
        content=question
    )
    query_embedding = resp.embedding

    # Pinecone 查询
    print(">>> querying Pinecone with vector")
    result = index.query(
        namespace=user_id,
        top_k=3,
        include_metadata=True,
        vector=query_embedding
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

    print(">>> calling Gemini")
    resp = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            top_p=0.95,
            thinking_config=types.ThinkingConfig(thinking_budget=2048)
        )
    )

    answer = resp.candidates[0].content.parts[0].text

    citations = [{
        "source": m.metadata["source"],
        "snippet": m.metadata["text"][:200],
        "anchor": f"{m.metadata['source']}_chunk_{m.metadata['chunk_index']}"
    } for m in result.matches]

    return {"answer": answer, "citations": citations}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
