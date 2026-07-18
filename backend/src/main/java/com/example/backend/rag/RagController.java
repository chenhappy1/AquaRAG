package com.example.backend.rag;

import java.time.Duration;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

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
    public ResponseEntity<String> uploadFile(@RequestParam("file") MultipartFile file) {
        ragService.ingestFile(file);
        return ResponseEntity.ok("uploaded");
    }

    @PostMapping(path = "/chat", consumes = MediaType.APPLICATION_JSON_VALUE)
    public SseEmitter chat(@RequestBody ChatRequest request) {
        SseEmitter emitter = new SseEmitter(Duration.ofMinutes(5).toMillis());
        try {
            var chunks = ragService.findTopChunks(request.question());
            emitter.send(SseEmitter.event().name("chunk").data("Retrieving relevant text from vector store..."));
            Thread.sleep(400);
            for (var chunk : chunks) {
                emitter.send(SseEmitter.event().name("chunk").data(chunk));
                Thread.sleep(250);
            }

            var chatResult = ragService.generateChatResult(request.question());
            var resultJson = OBJECT_MAPPER.writeValueAsString(chatResult);
            emitter.send(SseEmitter.event().name("result").data(resultJson, MediaType.APPLICATION_JSON));
            emitter.complete();
        } catch (Exception ex) {
            emitter.completeWithError(ex);
        }
        return emitter;
    }

    public record ChatRequest(String question) {}
}
