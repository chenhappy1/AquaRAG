# AquaRAG Architecture

## High-Level Architecture

```text
Browser / Angular UI
        |
        v
Spring Boot API
        |
        +--> Python RAG Service
        |
        +--> Auth / User logic
```

## Frontend Layer

The Angular frontend is a standalone-component application.

Key pieces:
- AppComponent: root shell for routing
- LoginComponent: user login UI
- RegisterComponent: user registration UI
- RagComponent: document upload and chat experience
- AuthService: handles authentication state and persistence
- JwtInterceptor: attaches the JWT token to API requests

## Backend Layer

The Java backend exposes REST endpoints used by the frontend.

Key pieces:
- RagController: handles upload and chat requests
- RagService: contains the core RAG workflow logic
- AuthController: handles auth-related endpoints

## AI Layer

The Python service is used for the retrieval and generation pipeline.

Typical flow:
1. Receive document input
2. Extract and chunk content
3. Build retrieval context
4. Answer the user question using the retrieved text

## Routing Model

The app uses Angular routes:
- /login
- /register
- /chat

The root component should remain a router container and not contain the entire app UI directly.
