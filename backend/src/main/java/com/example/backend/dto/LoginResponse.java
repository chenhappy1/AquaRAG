package com.example.backend.dto;

import java.util.UUID;

public record LoginResponse(String token, UserFields user) {
    public record UserFields(UUID id, String username, String email) {}
}
