# AquaRAG API Notes

## Authentication Endpoints

### POST /api/auth/login
Request body:
```json
{
  "username": "demo",
  "password": "demo"
}
```

Response:
```json
{
  "token": "jwt-token"
}
```

### POST /api/auth/register
Request body:
```json
{
  "username": "demo",
  "email": "demo@example.com",
  "password": "demo"
}
```

## RAG Endpoints

### POST /api/upload
- Accepts a file upload
- Returns upload status and chunk previews

### POST /api/chat
Request body:
```json
{
  "question": "What does this document say?"
}
```

Response:
```json
{
  "answer": "...",
  "citations": []
}
```

## Notes

- JWTs should be passed in the Authorization header.
- Authenticated requests should be scoped to the current user.
