import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

export interface AuthUser {
  id: string;
  firstname: string;
  lastname: string;
  email: string;
}

export interface AuthResponse {
  token?: string;
  user?: AuthUser;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly tokenStorageKey = 'aqarag.token';
  private readonly userStorageKey = 'aqarag.user';
  private readonly currentUserSignal = signal<AuthUser | null>(this.readStoredUser());

  constructor(private readonly http: HttpClient) {}

  login(credentials: { email: string; password: string }): Observable<AuthResponse> {
    // return this.http.post<AuthResponse>('/api/auth/login', credentials).pipe(
    return this.http.post<AuthResponse>('http://18.191.193.40/api/auth/login', credentials).pipe(
      tap((response) => this.persistSession(response))
    );
  }

  register(payload: { firstname: string; lastname: string; password: string; email: string }): Observable<AuthResponse> {
    // return this.http.post<AuthResponse>('/api/auth/register', payload).pipe(
    return this.http.post<AuthResponse>('http://18.191.193.40/api/auth/register', payload).pipe(
      tap((response) => {
        if (response?.token && response?.user) {
          this.persistSession(response);
        }
      })
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
    const token = response.token;
    const user = response.user;

    if (!token || !user) {
      return;
    }

    localStorage.setItem(this.tokenStorageKey, token);
    localStorage.setItem(this.userStorageKey, JSON.stringify(user));
    this.currentUserSignal.set(user);
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