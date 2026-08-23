from fastapi import FastAPI, UploadFile, File, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from bs4 import BeautifulSoup
from docx import Document
from PyPDF2 import PdfReader
from pinecone import Pinecone
from google import genai
from google.genai import types
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
#  Pinecone 初始化
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
#  列出用户所有文件（刷新恢复）
# ---------------------------
@app.get("/api/rag/files")
async def list_user_files(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "")
    claims = decode_jwt(token)
    user_id = claims["sub"]

    # 查询 Pinecone 中所有属于该用户的 chunks
    result = index.query(
        namespace=user_id,
        top_k=1000,
        include_metadata=True,
        vector=[0] * 1024
    )

    files = {}
    for m in result.matches:
        src = m.metadata["source"]
        if src not in files:
            files[src] = {
                "filename": src,
                "chunks": []
            }
        files[src]["chunks"].append({
            "ref": src,
            "snippet": m.metadata["text"][:200],
            "anchor": f"{src}_chunk_{m.metadata['chunk_index']}"
        })

    return list(files.values())



# ---------------------------
#  上传文档 → 自动更新 S3 + Pinecone
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

    filename = file.filename
    s3_key = f"uploads/{user_id}/{filename}"

    # ---------------------------
    # ① 删除旧 Pinecone chunks
    # ---------------------------
    print(">>> checking old Pinecone chunks")

    old_chunks = index.query(
        namespace=user_id,
        top_k=1000,
        include_metadata=True,
        filter={"source": {"$eq": filename}},
        vector=[0] * 1024
    )

    if old_chunks.matches:
        ids = [m.id for m in old_chunks.matches]
        index.delete(namespace=user_id, ids=ids)
        print(f">>> deleted {len(ids)} old chunks")

    # ---------------------------
    # ② 删除旧 S3 文件
    # ---------------------------
    print(">>> deleting old S3 file:", s3_key)

    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        print(">>> old S3 file deleted")
    except Exception as e:
        print(">>> no old S3 file found:", e)

    # ---------------------------
    # ③ 上传新文件到 S3
    # ---------------------------
    file_bytes = await file.read()
    file_stream = BytesIO(file_bytes)

    print(">>> uploading new file to S3:", s3_key)
    try:
        s3.upload_fileobj(file_stream, S3_BUCKET, s3_key)
        print(">>> S3 upload SUCCESS")
    except Exception as e:
        print(">>> S3 upload FAILED:", e)
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {e}")

    # ---------------------------
    # ④ 提取文本
    # ---------------------------
    print(">>> extracting text")
    text = extract_text_from_memory(filename, file_bytes)

    # ---------------------------
    # ⑤ 分块
    # ---------------------------
    print(">>> splitting text")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(text)

    # ---------------------------
    # ⑥ 重新 embedding
    # ---------------------------
    print(">>> generating embeddings")
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    pinecone_records = []

    for idx, chunk in enumerate(chunks):
        resp = client.models.embed_content(
            model="gemini-embedding-001",
            contents=chunk,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=1024
            )
        )
        embedding = resp.embeddings[0].values

        pinecone_records.append({
            "id": f"{user_id}_{filename}_chunk_{idx+1}",
            "values": embedding,
            "metadata": {
                "text": chunk,
                "source": filename,
                "s3_key": s3_key,
                "chunk_index": idx + 1,
                "user_id": user_id
            }
        })

    print(">>> upserting new chunks")
    index.upsert(namespace=user_id, vectors=pinecone_records)

    # ---------------------------
    # ⑦ 返回新的 chunk previews
    # ---------------------------
    chunk_previews = [
        {
            "ref": filename,
            "snippet": chunk[:200],
            "anchor": f"{filename}_chunk_{i+1}"
        }
        for i, chunk in enumerate(chunks)
    ]

    return {
        "status": "updated",
        "filename": filename,
        "s3_key": s3_key,
        "message": f"Updated file and saved {len(chunks)} new chunks to Pinecone!",
        "chunk_previews": chunk_previews
    }


# ---------------------------
#  内存文本提取
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
#  Chat → embedding → Pinecone → Gemini
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

    client = genai.Client()

    # embedding 查询向量
    resp = client.models.embed_content(
        model="gemini-embedding-001",
        contents=question,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=1024
        )
    )
    query_embedding = resp.embeddings[0].values

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

    print(">>> calling Gemini")
    # resp = client.models.generate_content(
    #     model="gemini-3.1-flash-lite",
    #     contents=prompt,
    #     config=types.GenerateContentConfig(
    #         response_mime_type="application/json",
    #         top_p=0.95,
    #         thinking_config=types.ThinkingConfig(thinking_budget=2048)
    #     )
    # )

    resp = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            top_p=0.95
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
