package com.example.backend.rag.controller;

import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class AuthController {

    @PostMapping("/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody LoginRequest request) {
        if ("chenfei".equals(request.username()) && "123456".equals(request.password())) {
            String token = "demo-jwt-token-for-" + request.username();
            return ResponseEntity.ok(Map.of(
                "token", token,
                "user", Map.of(
                    "id", 1,
                    "username", request.username(),
                    "email", "chenfei@example.com"
                )
            ));
        }

        return ResponseEntity.status(401).body(Map.of("message", "Invalid credentials"));
    }

    @PostMapping("/register")
    public ResponseEntity<Map<String, Object>> register(@RequestBody RegisterRequest request) {
        String token = "demo-jwt-token-for-" + request.username();
        return ResponseEntity.ok(Map.of(
            "token", token,
            "user", Map.of(
                "id", 2,
                "username", request.username(),
                "email", request.email()
            )
        ));
    }

    public record LoginRequest(String username, String password) {}

    public record RegisterRequest(String username, String password, String email) {}
}
