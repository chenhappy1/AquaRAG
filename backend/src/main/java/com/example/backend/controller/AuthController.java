package com.example.backend.controller;

import com.example.backend.dto.LoginRequest;
import com.example.backend.dto.LoginResponse;
import com.example.backend.dto.RegisterRequest;
import com.example.backend.dto.RegisterResponse;
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
    public ResponseEntity<LoginResponse> login(@RequestBody LoginRequest request) {
        return userRepository.findByFirstnameAndLastname(request.firstname(), request.lastname())
            .filter(user -> passwordEncoder.matches(request.password(), user.getPassword()))
            .map(user -> {
                String token = "demo-jwt-token-for-" + user.getFirstname() + " " + user.getLastname();
                LoginResponse.UserFields userFields = new LoginResponse.UserFields(user.getId(), user.getFirstname(), user.getLastname(), user.getEmail());
                return ResponseEntity.ok(new LoginResponse(token, userFields));
            })
            .orElseGet(() -> ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(null));
    }

    @PostMapping("/register")
    public ResponseEntity<RegisterResponse> register(@RequestBody RegisterRequest request) {
        System.out.println("Register request received: " + request);
        if (userRepository.existsByFirstnameAndLastname(request.firstname(), request.lastname())) {
            return ResponseEntity.badRequest().body(null);
        }
        if (userRepository.existsByEmail(request.email())) {
            return ResponseEntity.badRequest().body(null);
        }

        String encodedPassword = passwordEncoder.encode(request.password());
        User user = new User(request.firstname(), request.lastname(), request.email(), encodedPassword);

        User savedUser = userRepository.save(user);
        RegisterResponse response = new RegisterResponse(savedUser.getId(), savedUser.getFirstname(), savedUser.getLastname(), savedUser.getEmail());

        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }
}
