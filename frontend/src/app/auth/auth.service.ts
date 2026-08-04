import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

export interface AuthUser {
  id: number;
  username: string;
  email: string;
}

export interface AuthResponse {
  token: string;
  user: AuthUser;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly tokenStorageKey = 'aqarag.token';
  private readonly userStorageKey = 'aqarag.user';
  private readonly currentUserSignal = signal<AuthUser | null>(this.readStoredUser());

  constructor(private readonly http: HttpClient) {}

  login(credentials: { username: string; password: string }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>('/api/auth/login', credentials).pipe(
      tap((response) => this.persistSession(response))
    );
  }

  register(payload: { username: string; password: string; email: string }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>('/api/auth/register', payload).pipe(
      tap((response) => this.persistSession(response))
    );
  }

  logout(): void {
    localStorage.removeItem(this.tokenStorageKey);
    localStorage.removeItem(this.userStorageKey);
    this.currentUserSignal.set(null);
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenStorageKey);
  }

  currentUser(): AuthUser | null {
    return this.currentUserSignal();
  }

  isAuthenticated(): boolean {
    return Boolean(this.getToken());
  }

  private persistSession(response: AuthResponse): void {
    localStorage.setItem(this.tokenStorageKey, response.token);
    localStorage.setItem(this.userStorageKey, JSON.stringify(response.user));
    this.currentUserSignal.set(response.user);
  }

  private readStoredUser(): AuthUser | null {
    const rawUser = localStorage.getItem(this.userStorageKey);
    if (!rawUser) {
      return null;
    }

    try {
      return JSON.parse(rawUser) as AuthUser;
    } catch {
      return null;
    }
  }
}
