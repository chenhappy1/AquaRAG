import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { AuthService } from '../auth/auth.service';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class RagService {
  constructor(
    private readonly http: HttpClient,
    private readonly auth: AuthService
  ) {}

  private authHeaders(): HttpHeaders {
    return new HttpHeaders({
      Authorization: `Bearer ${this.auth.getToken() ?? ''}`,
    });
  }

  uploadFile(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post('/api/rag/upload', formData, {
      headers: this.authHeaders(),
    });
  }

  chat(question: string): Observable<any> {
    return this.http.post(
      '/api/rag/chat',
      { question },
      {
        headers: this.authHeaders().set('Content-Type', 'application/json'),
      }
    );
  }
}
