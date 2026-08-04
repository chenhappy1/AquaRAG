package com.example.backend.rag.controller;

import java.time.Duration;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import com.example.backend.rag.service.RagService;
import com.fasterxml.jackson.databind.ObjectMapper;

@RestController
@RequestMapping("/api")
public class RagController {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private final RagService ragService;

    @Autowired
    public RagController(RagService ragService) {
        this.ragService = ragService;
    }

    @PostMapping(path = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<String> uploadFile(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @RequestParam("file") MultipartFile file) {
        ragService.ingestFile(resolveUsername(authHeader), file);
        return ResponseEntity.ok("uploaded");
    }

    @PostMapping(path = "/chat", consumes = MediaType.APPLICATION_JSON_VALUE)
    public SseEmitter chat(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @RequestBody ChatRequest request) {
        String username = resolveUsername(authHeader);
        SseEmitter emitter = new SseEmitter(Duration.ofMinutes(5).toMillis());
        try {
            var chunks = ragService.findTopChunks(username, request.question());
            emitter.send(SseEmitter.event().name("chunk").data("Retrieving relevant text from vector store..."));
            Thread.sleep(400);
            for (var chunk : chunks) {
                emitter.send(SseEmitter.event().name("chunk").data(chunk));
                Thread.sleep(250);
            }

            var chatResult = ragService.generateChatResult(username, request.question());
            var resultJson = OBJECT_MAPPER.writeValueAsString(chatResult);
            emitter.send(SseEmitter.event().name("result").data(resultJson, MediaType.APPLICATION_JSON));
            emitter.complete();
        } catch (Exception ex) {
            emitter.completeWithError(ex);
        }
        return emitter;
    }

    private String resolveUsername(String authHeader) {
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            String token = authHeader.substring(7);
            if (token.startsWith("demo-jwt-token-for-")) {
                return token.substring("demo-jwt-token-for-".length());
            }
        }
        return "anonymous";
    }

    public record ChatRequest(String question) {}
}
