import os
import json
import pika
from io import BytesIO
from pathlib import Path
from bs4 import BeautifulSoup
from docx import Document
from PyPDF2 import PdfReader
from pinecone import Pinecone
from google import genai
from google.genai import types
from langchain_text_splitters import RecursiveCharacterTextSplitter
import boto3
import requests

# Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = os.getenv("PINECONE_INDEX_NAME")
index = pc.Index(index_name)

# S3
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)
S3_BUCKET = os.getenv("AWS_S3_BUCKET")

# RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=RABBITMQ_HOST)
)
channel = connection.channel()
channel.queue_declare(queue="rag_upload_jobs", durable=True)

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

def process_job(ch, method, properties, body):
    job = json.loads(body)
    user_id = job["user_id"]
    filename = job["filename"]
    s3_key = job["s3_key"]

    print(f">>> worker: processing job for user={user_id}, file={filename}, s3_key={s3_key}")

    # 从 S3 读文件
    obj = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
    file_bytes = obj["Body"].read()

    # 提取文本
    text = extract_text_from_memory(filename, file_bytes)

    # 分块
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(text)

    # embedding
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

    print(">>> worker: upserting new chunks")
    index.upsert(namespace=user_id, vectors=pinecone_records)

    # 告诉 RabbitMQ：这个消息处理完了
    ch.basic_ack(delivery_tag=method.delivery_tag)
requests.post(
    "http://localhost:8000/api/rag/notify",
    json={
        "user_id": user_id,
        "filename": filename
    }
)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue="rag_upload_jobs", on_message_callback=process_job)

print(">>> worker started, waiting for jobs...")
channel.start_consuming()