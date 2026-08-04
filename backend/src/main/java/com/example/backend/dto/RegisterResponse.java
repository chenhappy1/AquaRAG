package com.example.backend.dto;

import java.util.UUID;

public record RegisterResponse(UUID id, String firstname, String lastname, String email) {}
