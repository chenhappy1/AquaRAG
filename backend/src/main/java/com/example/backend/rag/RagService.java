package com.example.backend.rag;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

import org.apache.tika.Tika;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class RagService {

    private record DocumentChunk(String id, String text, int page) {}

    public record Citation(int page, String text, String ref) {}

    public record ChatResult(String answer, List<Citation> citations) {}

    private final List<DocumentChunk> memory = new CopyOnWriteArrayList<>();
    private final Tika tika = new Tika();

    public void ingestFile(MultipartFile file) {
        try {
            String text = tika.parseToString(file.getInputStream());
            List<String> chunks = chunkText(text);
            AtomicInteger pageCounter = new AtomicInteger(memory.size() / 3);
            memory.addAll(chunks.stream()
                    .map(chunk -> new DocumentChunk(generateId(), chunk, pageCounter.incrementAndGet()))
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

    public ChatResult generateChatResult(String question) {
        var queryTerm = question.toLowerCase().split("\\s+", 2)[0];
        var best = memory.stream()
                .filter(chunk -> chunk.text().toLowerCase().contains(queryTerm))
                .findFirst();

        var citations = memory.stream()
                .filter(chunk -> chunk.text().toLowerCase().contains(queryTerm))
                .limit(3)
                .map(chunk -> new Citation(chunk.page(), snippet(chunk.text()), "page-" + chunk.page()))
                .collect(Collectors.toList());

        String answerText;
        if (best.isPresent()) {
            DocumentChunk chunk = best.get();
            answerText = "Based on your document, the most relevant passage is on page " + chunk.page() + ": "
                    + chunk.text() + "\n\nThis response includes citation markers for each source reference.";
        } else {
            answerText = "No matching content found in the uploaded document. Please try a different question.";
        }

        return new ChatResult(answerText, citations);
    }

    private String snippet(String text) {
        if (text.length() <= 120) {
            return text;
        }
        return text.substring(0, 120).trim() + "...";
    }

    public List<String> findTopChunks(String question) {
        return memory.stream()
                .filter(chunk -> chunk.text().toLowerCase().contains(question.toLowerCase().split("\\s+", 2)[0]))
                .limit(3)
                .map(DocumentChunk::text)
                .collect(Collectors.toList());
    }
}
