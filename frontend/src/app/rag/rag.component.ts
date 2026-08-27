import { Component, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../auth/auth.service';
import { RagService } from './rag.service';

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
  selector: 'app-rag',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './rag.component.html',
  styleUrls: ['./rag.component.scss'],
})
export class RagComponent implements OnInit {
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

  constructor(
    public readonly authService: AuthService,
    private readonly router: Router,
    private readonly ragService: RagService
  ) {
    this.loadUserFiles();   // 刷新后自动恢复文件
  }

  /* ===========================
     自动加载用户文件（刷新恢复）
  ============================ */

  ngOnInit() {
    this.ragService.getEvents().subscribe(event => {
      console.log('组件收到 SSE：', event);

      if (event.status === 'done') {
        // 后端处理完成 → 切换为 active 并重新加载文件/chunks
        this.stage.set('active');
        this.loadUserFiles();
        alert('文件处理完成！');
      }
    });
  }

  protected async loadUserFiles() {
    try {
      const files = await this.ragService.listFiles().toPromise();

      if (!files || files.length === 0) {
        this.stage.set('empty');
        return;
      }

      this.uploadedFiles.set(
        files.map(f => new File([], f.filename))
      );

      this.selectedFileIndex.set(0);
      this.chunkPreviews.set(files[0].chunks);
      this.stage.set('active');
    } catch (err) {
      console.error('Failed to load files', err);
      this.stage.set('empty');
    }
  }

  /* ===========================
     GETTERS
  ============================ */

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

  /* ===========================
     FILE UPLOAD
  ============================ */

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

    const uploadPromise = this.ragService.uploadFile(file).toPromise();

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
      await uploadPromise;          // 这里只负责上传 + 排队，不再假装处理完成
      await intervalPromise;
      // 不在这里切换为 active，等 SSE 通知再切换
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
    this.loadChunksForFile(selectedIndex);
    this.stage.set('active');
  }

  protected async loadChunksForFile(index: number) {
    const filename = this.uploadedFiles()[index].name;

    try {
      const files = await this.ragService.listFiles().toPromise();

      if (!files || files.length === 0) {
        console.warn('No files returned from backend');
        return;
      }

      const file = files.find(f => f.filename === filename);

      if (file && file.chunks) {
        this.chunkPreviews.set(file.chunks);
      } else {
        console.warn('No chunks found for file:', filename);
      }
    } catch (err) {
      console.error('Failed to load chunks', err);
    }
  }

  /* ===========================
     CHAT
  ============================ */

  protected sendChat(): void {
    const message = this.chatInput().trim();
    if (!message || this.chatStreaming()) return;

    const userMessage: ChatMessage = { role: 'user', text: message };
    this.chatMessages.set([...this.chatMessages(), userMessage]);
    this.chatInput.set('');

    this.scrollToBottom();
    this.startChatStream(message);
  }

  protected async startChatStream(question: string): Promise<void> {
    if (this.chatStreaming()) return;
    this.chatStreaming.set(true);

    const assistantMessage: ChatMessage = { role: 'assistant', text: 'Thinking...' };
    const messages = [...this.chatMessages(), assistantMessage];
    this.chatMessages.set(messages);

    this.scrollToBottom();

    const targetIndex = messages.length - 1;

    try {
      const response: any = await this.ragService.chat(question).toPromise();

      const answer = response?.answer || 'No answer returned.';
      const citations = response?.citations || [];

      this.updateAssistantMessage(targetIndex, answer.trim(), citations);
      this.scrollToBottom();
    } catch (error) {
      console.error(error);
      this.chatMessages.set([
        ...this.chatMessages().slice(0, targetIndex),
        { role: 'assistant', text: 'Unable to complete the chat request. Please try again.' },
      ]);
      this.scrollToBottom();
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
    this.scrollToBottom();
  }

  /* ===========================
     CITATION JUMP
  ============================ */

  protected openCitation(reference: string): void {
    this.activeCitation.set(reference);
    window.setTimeout(() => {
      const anchor = document.querySelector(`[data-ref="${reference}"]`);
      if (anchor instanceof HTMLElement) {
        anchor.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 80);
  }

  /* ===========================
     SIDEBAR
  ============================ */

  protected logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  protected toggleSidebar(): void {
    this.sidebarCollapsed.update((value) => !value);
  }

  /* ===========================
     AUTO SCROLL
  ============================ */

  scrollToBottom() {
    setTimeout(() => {
      const el = document.querySelector('.chat-messages');
      if (el) el.scrollTop = el.scrollHeight;
    }, 0);
  }

  handleKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter' && !this.chatStreaming()) {
      event.preventDefault();
      this.sendChat();
    }
  }
}