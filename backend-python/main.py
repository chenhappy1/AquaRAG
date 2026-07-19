from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, OpenAI
import shutil
import os
import json

app = FastAPI()

# Enable CORS so your Angular frontend (localhost:4200) can talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploaded_files"
DB_DIR = "./chroma_db"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    # 1. Save the incoming file from frontend locally
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 2. Read the text content (Example assumes a plain text .txt file)
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
        
    # 3. Chunk the text into smaller pieces (Crucial for RAG)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_text(text)
    
    # 4. Convert chunks to embeddings and save to local Chroma vector database
    # NOTE: You must set your OPENAI_API_KEY as an environment variable before running this
    # Use the lower-cost embedding model for cheaper RAG vectorization
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    db = Chroma.from_texts(chunks, embeddings, persist_directory=DB_DIR)
    
    return {
        "status": "success",
        "filename": file.filename,
        "message": f"Successfully split into {len(chunks)} chunks and saved to Vector DB!"
    }


def load_vector_store():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return Chroma(persist_directory=DB_DIR, embedding_function=embeddings)


def build_prompt(question: str, docs: list[any]) -> str:
    if docs:
        context = "\n\n".join([getattr(doc, "page_content", "") for doc in docs])
    else:
        context = ""

    return (
        "You are a helpful assistant. Use the provided document excerpts to answer the question. "
        "If the answer is not contained in the excerpts, say you do not know.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer concisely and cite any source references if available."
    )


@app.post("/api/chat")
async def chat(request: Request):
    payload = await request.json()
    question = payload.get("question", "").strip()
    if not question:
        return {"error": "Question is required."}

    if not os.path.exists(DB_DIR):
        return {"error": "Vector database not found. Please upload a document first."}

    db = load_vector_store()
    docs = db.similarity_search(question, k=3)

    prompt = build_prompt(question, docs)
    llm = OpenAI(model="DeepSeek-V3", temperature=0.2, max_tokens=512)
    answer = llm.predict(prompt)

    citations = []
    for index, doc in enumerate(docs, start=1):
        source = getattr(doc, "metadata", {}).get("source", f"document_{index}")
        citations.append({"source": source, "snippet": getattr(doc, "page_content", "")[:200]})

    async def event_stream():
        chunk_size = 120
        for start in range(0, len(answer), chunk_size):
            chunk = answer[start : start + chunk_size]
            yield f"event: chunk\ndata: {chunk}\n\n"

        result_payload = {
            "answer": answer,
            "citations": citations,
        }
        yield f"event: result\ndata: {json.dumps(result_payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")