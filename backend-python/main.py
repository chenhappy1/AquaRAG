from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
import shutil
import os

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
    embeddings = OpenAIEmbeddings() 
    db = Chroma.from_texts(chunks, embeddings, persist_directory=DB_DIR)
    
    return {
        "status": "success", 
        "filename": file.filename,
        "message": f"Successfully split into {len(chunks)} chunks and saved to Vector DB!"
    }