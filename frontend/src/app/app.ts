import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

interface HistoryItem {
  title: string;
  time: string;
  status: string;
}

interface Citation {
  page: number;
  text: string;
  ref: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  citations?: Citation[];
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
      await Promise.all([uploadPromise, intervalPromise]);
    } catch (error) {
      console.error('Upload failed', error);
    } finally {
      this.stage.set('active');
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
    this.chatMessages.set([...this.chatMessages(), { role: 'user', text: message }]);
    this.chatInput.set('');
    this.startChatStream(message);
  }

  protected async startChatStream(question: string): Promise<void> {
    if (this.chatStreaming()) return;
    this.chatStreaming.set(true);

    const messages = [...this.chatMessages(), { role: 'assistant', text: '' }];
    this.chatMessages.set(messages);
    const targetIndex = messages.length - 1;

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        throw new Error(`Chat request failed with status ${response.status}`);
      }

      if (!response.body) {
        throw new Error('Streaming response not available');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let eventName = '';
      let eventData = '';
      let currentText = '';

      const emitEvent = () => {
        if (!eventName && !eventData) return;
        const data = eventData.trim();
        if (eventName === 'chunk') {
          currentText += data + '\n';
          this.updateAssistantMessage(targetIndex, currentText.trim());
        } else if (eventName === 'result') {
          try {
            const payload = JSON.parse(data);
            currentText = payload.answer || currentText;
            this.updateAssistantMessage(targetIndex, currentText.trim(), payload.citations || []);
          } catch (err) {
            this.updateAssistantMessage(targetIndex, `Failed to parse chat response: ${err}`);
          }
        }
        eventName = '';
        eventData = '';
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line) {
            emitEvent();
            continue;
          }
          if (line.startsWith('event:')) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            const dataLine = line.slice(5).trimStart();
            eventData += (eventData ? '\n' : '') + dataLine;
          }
        }
      }

      if (buffer.length > 0) {
        if (buffer.startsWith('event:')) {
          eventName = buffer.slice(6).trim();
        } else if (buffer.startsWith('data:')) {
          eventData += buffer.slice(5).trimStart();
        }
        emitEvent();
      }
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
