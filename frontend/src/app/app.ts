import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { FileUploadModule } from 'primeng/fileupload';
import { ProgressBarModule } from 'primeng/progressbar';
import { SkeletonModule } from 'primeng/skeleton';
import { InputTextModule } from 'primeng/inputtext';

interface HistoryItem {
  title: string;
  time: string;
  status: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ButtonModule, FileUploadModule, ProgressBarModule, SkeletonModule, InputTextModule],
  templateUrl: './app.html',
  styleUrls: ['./app.scss'],
})
export class App {
  protected readonly stage = signal<'empty' | 'processing' | 'active'>('empty');
  protected readonly uploadedFiles = signal<File[]>([]);
  protected readonly selectedFileIndex = signal(0);
  protected readonly processingStep = signal(0);
  protected readonly activeCitation = signal<string | null>(null);
  protected readonly sidebarCollapsed = signal(false);
  protected readonly chatInput = signal('');
  protected readonly chatMessages = signal<{ role: 'user' | 'assistant'; text: string }[]>([]);
  protected readonly chatStreaming = signal(false);

  protected get selectedFile(): File | null {
    return this.uploadedFiles()[this.selectedFileIndex()] ?? null;
  }

  protected get selectedFileName(): string {
    return this.selectedFile?.name ?? 'Untitled document';
  }

  protected get documentSummary(): string {
    return 'This document has been parsed and split into searchable chunks for accurate answers with source citations.';
  }

  protected get samplePrompts() {
    return [
      'Summarize key findings',
      'What are the contract terms?',
      'List the main risks',
      'Where are the deadlines specified?',
    ];
  }

  protected get historyItems(): HistoryItem[] {
    return [
      { title: 'Uploaded contract.pdf', time: '2m ago', status: 'Processed' },
      { title: 'Asked about timelines', time: 'Just now', status: 'Answered' },
      { title: 'Uploaded meeting-notes.txt', time: 'Yesterday', status: 'Ready' },
    ];
  }

  protected onFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;
    this.onFileUpload(input.files[0]);
    input.value = '';
  }

  protected onDrop(event: DragEvent): void {
    event.preventDefault();
    const file = event.dataTransfer?.files?.[0];
    this.onFileUpload(file);
  }

  protected onDragOver(event: DragEvent): void {
    event.preventDefault();
  }

  protected onFileUpload(file?: File | null): void {
    if (!file) return;
    const files = [...this.uploadedFiles(), file];
    this.uploadedFiles.set(files);
    this.selectedFileIndex.set(files.length - 1);
    this.stage.set('processing');
    this.processingStep.set(0);
    this.activeCitation.set(null);
    this.chatMessages.set([]);
    this.chatInput.set('');
    this.chatStreaming.set(false);

    const interval = window.setInterval(() => {
      const nextStep = this.processingStep() + 1;
      if (nextStep >= 3) {
        window.clearInterval(interval);
        this.stage.set('active');
        return;
      }
      this.processingStep.set(nextStep);
    }, 800);
  }

  protected processingText(): string {
    const labels = ['Uploading file...', 'Analyzing text...', 'Building knowledge base...'];
    return labels[this.processingStep()] || labels[0];
  }

  protected selectFile(index: number | string): void {
    const selectedIndex = typeof index === 'string' ? Number(index) : index;
    if (selectedIndex < 0 || selectedIndex >= this.uploadedFiles().length) return;
    this.selectedFileIndex.set(selectedIndex);
    this.activeCitation.set(null);
    this.stage.set('active');
  }

  protected sendChat(): void {
    const message = this.chatInput().trim();
    if (!message || this.chatStreaming()) return;
    this.chatMessages.set([...this.chatMessages(), { role: 'user', text: message }]);
    this.chatInput.set('');
    this.startMockResponse();
  }

  protected startMockResponse(): void {
    if (this.chatStreaming()) return;
    this.chatStreaming.set(true);
    const response = 'The model is preparing an answer. It will reference the uploaded document and include source citations when the backend is connected.';
    const messages = [...this.chatMessages(), { role: 'assistant', text: '' }];
    this.chatMessages.set(messages);
    const targetIndex = messages.length - 1;
    let position = 0;

    const interval = window.setInterval(() => {
      position += 1;
      const currentText = response.slice(0, position);
      const updated = this.chatMessages().map((item, index) =>
        index === targetIndex ? { ...item, text: currentText } : item
      );
      this.chatMessages.set(updated);

      if (position >= response.length) {
        window.clearInterval(interval);
        this.chatStreaming.set(false);
      }
    }, 30);
  }

  protected openCitation(reference: string): void {
    this.activeCitation.set(reference);
    window.setTimeout(() => {
      const anchor = document.querySelector(`[data-ref="${reference}"]`);
      if (anchor instanceof HTMLElement) {
        anchor.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 80);
  }

  protected copyResponse(): void {
    navigator.clipboard.writeText('The document outlines the main contract terms, deadlines, and risk assumptions.');
  }

  protected toggleSidebar(): void {
    this.sidebarCollapsed.update((value) => !value);
  }
}
