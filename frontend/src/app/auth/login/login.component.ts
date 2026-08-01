import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent {
  protected readonly form;
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly isSubmitting = signal(false);

  constructor(
    private readonly formBuilder: FormBuilder,
    private readonly authService: AuthService,
    private readonly router: Router
  ) {
    this.form = this.formBuilder.group({
      username: ['', [Validators.required]],
      password: ['', [Validators.required]],
    });
  }

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const { username, password } = this.form.getRawValue();
    if (!username || !password) {
      return;
    }

    this.errorMessage.set(null);
    this.isSubmitting.set(true);

    this.authService.login({ username, password }).subscribe({
      next: () => this.router.navigate(['/chat']),
      error: () => {
        this.errorMessage.set('Invalid username or password.');
        this.isSubmitting.set(false);
      },
    });
  }
}
