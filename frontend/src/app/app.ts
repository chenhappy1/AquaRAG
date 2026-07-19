import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

interface HistoryItem {
  title: string;
  time: string;
  status: string;
}

interface Citation {
  source: string;
  snippet: string;
  anchor?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  citations?: Citation[];
}

interface ChunkPreview {
  ref: string;
  snippet: string;
  anchor: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.html',
  styleUrls: ['./app.scss'],
})
export class App {
  protected readonly stage = signal<'empty' | 'processing' | 'active'>('empty');
  protected readonly uploadedFiles = signal<File[]>([]);
  protected readonly selectedFileIndex = signal(0);
  protected readonly processingStep = signal(0);
  protected readonly activeCitation = signal<string | null>(null);
  protected readonly chunkPreviews = signal<ChunkPreview[]>([]);
  protected readonly sidebarCollapsed = signal(false);
  protected readonly chatInput = signal('');
  protected readonly chatMessages = signal<ChatMessage[]>([]);
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

  protected async onFileUpload(file?: File | null): Promise<void> {
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

    const formData = new FormData();
    formData.append('file', file);

    const uploadPromise = fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });

    const intervalPromise = new Promise<void>((resolve) => {
      const interval = window.setInterval(() => {
        const nextStep = this.processingStep() + 1;
        if (nextStep >= 3) {
          window.clearInterval(interval);
          resolve();
          return;
        }
        this.processingStep.set(nextStep);
      }, 800);
    });

    try {
      const response = await uploadPromise;
      const result = await response.json();
      if (!response.ok || result.status !== 'success') {
        throw new Error(result.message || `Upload failed with status ${response.status}`);
      }
      this.chunkPreviews.set(result.chunk_previews || []);
      await intervalPromise;
      this.stage.set('active');
    } catch (error) {
      console.error('Upload failed', error);
      this.stage.set('empty');
    }
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
    const userMessage: ChatMessage = { role: 'user', text: message };
    this.chatMessages.set([...this.chatMessages(), userMessage]);
    this.chatInput.set('');
    this.startChatStream(message);
  }

  protected async startChatStream(question: string): Promise<void> {
    if (this.chatStreaming()) return;
    this.chatStreaming.set(true);

    const assistantMessage: ChatMessage = { role: 'assistant', text: 'Thinking...' };
    const messages = [...this.chatMessages(), assistantMessage];
    this.chatMessages.set(messages);
    const targetIndex = messages.length - 1;

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        throw new Error(`Chat request failed with status ${response.status}`);
      }

      const payload = await response.json();
      const answer = payload.answer || 'No answer returned.';
      const citations = payload.citations || [];
      this.updateAssistantMessage(targetIndex, answer.trim(), citations);
    } catch (error) {
      console.error(error);
      this.chatMessages.set([
        ...this.chatMessages().slice(0, targetIndex),
        { role: 'assistant', text: 'Unable to complete the chat request. Please try again.' },
      ]);
    } finally {
      this.chatStreaming.set(false);
    }
  }

  protected updateAssistantMessage(index: number, text: string, citations: Citation[] = []): void {
    const updated = this.chatMessages().map((item, idx) =>
      idx === index
        ? { ...item, text, citations: item.role === 'assistant' ? citations : item.citations }
        : item
    );
    this.chatMessages.set(updated);
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
