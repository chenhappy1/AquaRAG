package com.example.backend.rag;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.stream.Collectors;

import org.apache.tika.Tika;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class RagService {

    private record DocumentChunk(String id, String text) {}

    private final List<DocumentChunk> memory = new CopyOnWriteArrayList<>();
    private final Tika tika = new Tika();

    public void ingestFile(MultipartFile file) {
        try {
            String text = tika.parseToString(file.getInputStream());
            List<String> chunks = chunkText(text);
            memory.addAll(chunks.stream()
                    .map(chunk -> new DocumentChunk(generateId(), chunk))
                    .collect(Collectors.toList()));
        } catch (Exception ex) {
            throw new IllegalStateException("Failed to ingest file", ex);
        }
    }

    private List<String> chunkText(String text) {
        int chunkSize = 800;
        int overlap = 200;
        List<String> chunks = new ArrayList<>();
        int position = 0;
        while (position < text.length()) {
            int end = Math.min(position + chunkSize, text.length());
            chunks.add(text.substring(position, end).trim());
            position += Math.max(1, chunkSize - overlap);
        }
        return chunks.stream().filter(chunk -> !chunk.isBlank()).collect(Collectors.toList());
    }

    private String generateId() {
        return "chunk-" + System.currentTimeMillis() + "-" + (memory.size() + 1);
    }

    public String mockChatResponse(String question) {
        var best = memory.stream()
                .filter(chunk -> chunk.text().toLowerCase().contains(question.toLowerCase().split("\\s+", 2)[0]))
                .findFirst()
                .map(DocumentChunk::text)
                .orElse("No matching content found in the uploaded document.");

        return "Based on your document, I found the relevant text: " + best + "\n\n(这是一个模拟回答，后端RAG管道已接入后将返回真实结果。)";
    }

    public List<String> findTopChunks(String question) {
        return memory.stream()
                .map(DocumentChunk::text)
                .limit(3)
                .collect(Collectors.toList());
    }
}
