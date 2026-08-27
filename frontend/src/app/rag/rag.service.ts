import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { AuthService } from '../auth/auth.service';
import { Observable, Subject } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class RagService {
  private sseEvents = new Subject<any>();
  private eventSource: EventSource | null = null;

  constructor(
    private readonly http: HttpClient,
    private readonly auth: AuthService
  ) {}

  /** ⭐ 在用户登录后调用，建立 SSE 连接 */
  connectSSE(userId: string) {
    if (!userId) {
      console.error("无法建立 SSE：userId 为空");
      return;
    }

    // 你的 FastAPI 是跑在 8000 端口
    this.eventSource = new EventSource(`/api/rag/sse?userId=${userId}`);

    this.eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("SSE 收到通知：", data);
      this.sseEvents.next(data);
    };

    this.eventSource.onerror = (err) => {
      console.error("SSE 错误：", err);
    };
  }

  /** ⭐ 组件订阅 SSE */
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

  listFiles(): Observable<any[]> {
    return this.http.get<any[]>('/api/rag/files', {
      headers: this.authHeaders(),
    });
  }
}