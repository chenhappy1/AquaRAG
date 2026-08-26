import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { AuthService } from '../auth/auth.service';
import { Observable } from 'rxjs';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class RagService {
  private sseEvents = new Subject<any>();
  constructor(
    private readonly http: HttpClient,
    private readonly auth: AuthService
  ) {
    this.initSSE();
  }

  private initSSE() {
    const userId = localStorage.getItem('userId'); // 或从 JWT 解析
    const eventSource = new EventSource(`http://localhost:9000/api/rag/sse?userId=${userId}`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("SSE 收到通知：", data);
      this.sseEvents.next(data);
    };

    eventSource.onerror = (err) => {
      console.error("SSE 错误：", err);
    };
  }

  getEvents() {
    return this.sseEvents.asObservable();
  }

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

  /** ⭐ 新增：列出用户文件（刷新恢复） */
  listFiles(): Observable<any[]> {
    return this.http.get<any[]>('/api/rag/files', {
      headers: this.authHeaders(),
    });
  }
}
