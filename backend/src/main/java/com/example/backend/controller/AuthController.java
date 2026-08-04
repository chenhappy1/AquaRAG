package com.example.backend.controller;

import com.example.backend.dto.UserDTO;
import com.example.backend.model.User;
import com.example.backend.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final UserRepository userRepository;
    private final BCryptPasswordEncoder passwordEncoder;

    @PostMapping("/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody LoginRequest request) {
        return userRepository.findByUsername(request.username())
            .filter(user -> passwordEncoder.matches(request.password(), user.getPassword()))
            .map(user -> {
                String token = "demo-jwt-token-for-" + user.getUsername();
                return ResponseEntity.ok(Map.<String, Object>of(
                    "token", token,
                    "user", Map.<String, Object>of(
                        "id", user.getId(),
                        "username", user.getUsername(),
                        "email", user.getEmail()
                    )
                ));
            })
            .orElseGet(() -> ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.<String, Object>of("message", "Invalid credentials")));
    }

    @PostMapping("/register")
    public ResponseEntity<UserDTO> register(@RequestBody RegisterRequest request) {
        if (userRepository.existsByUsername(request.username())) {
            return ResponseEntity.badRequest().body(null);
        }
        if (userRepository.existsByEmail(request.email())) {
            return ResponseEntity.badRequest().body(null);
        }

        String encodedPassword = passwordEncoder.encode(request.password());
        User user = User.builder()
            .username(request.username())
            .email(request.email())
            .password(encodedPassword)
            .build();

        User savedUser = userRepository.save(user);
        UserDTO userDTO = new UserDTO(savedUser.getId(), savedUser.getUsername(), savedUser.getEmail());

        return ResponseEntity.status(HttpStatus.CREATED).body(userDTO);
    }

    public record LoginRequest(String username, String password) {}

    public record RegisterRequest(String username, String password, String email) {}
}
