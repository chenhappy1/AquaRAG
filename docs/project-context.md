# AquaRAG Project Context

## 1. Project Overview

AquaRAG is a document-based question answering application that combines a frontend UI, a Java Spring Boot backend, and a Python RAG service.

The system allows users to:
- sign up and log in
- upload documents
- ask questions about uploaded content
- receive answers with source-like citations

## 2. Current Tech Stack

### Frontend
- Angular 22
- TypeScript
- Standalone components
- Reactive forms
- Angular Router

### Backend
- Java 17
- Spring Boot
- REST APIs
- JWT-based authentication demo flow

### AI / RAG Service
- Python
- FastAPI-style request handling in the backend-python service
- Document ingestion and retrieval workflow

## 3. Repository Structure

```text
backend/
  src/main/java/com/example/backend/
    rag/
      RagController.java
      RagService.java
      AuthController.java

backend-python/
  main.py
  requirements.txt

frontend/
  src/app/
    auth/
    layout/
    rag/
    app.routes.ts
    app.component.ts
    app.html
```

## 4. Main Responsibilities

### Frontend
The Angular app is responsible for:
- rendering login and registration screens
- routing between auth and chat pages
- sending upload and chat requests to the backend
- storing and reading the JWT token in browser storage

### Backend (Java)
The Spring Boot backend is responsible for:
- authentication endpoints
- JWT handling
- upload and chat endpoints
- user-scoped document/chat context

### Python RAG Service
The Python service is responsible for:
- document processing
- chunking and retrieval logic
- answering user questions based on uploaded content

## 5. Authentication Flow

1. A user opens the app and goes to the login or register page.
2. The frontend sends authentication credentials to the backend.
3. The backend validates the credentials and returns a JWT token.
4. The frontend stores the token and sends it in the Authorization header for future API calls.
5. Protected routes such as /chat require a valid token.

## 6. RAG Flow

1. The user uploads a document.
2. The backend receives the file and forwards the request to the RAG processing pipeline.
3. The document is split into chunks and prepared for retrieval.
4. The user asks a question.
5. Relevant chunks are retrieved and used to generate an answer.
6. The answer is returned to the frontend with supporting context.

## 7. Important Business Rules

- Authentication is required for chat access.
- Upload and chat operations should be associated with the logged-in user.
- The app should remain route-based, with the root shell only acting as a router container.
- Login, register, and RAG pages should remain separate components.

## 8. Current Development Status

### Completed
- Angular route-based auth and chat structure
- login/register components
- JWT interceptor and auth guard
- dedicated RAG component
- backend auth and RAG endpoints

### In Progress
- production-grade persistence and DB integration
- richer document parsing and embedding pipeline
- full multi-user security hardening
- deployment and observability improvements
