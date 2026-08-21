package com.example.backend.controller;

import com.example.backend.config.JwtUtil;
import com.example.backend.dto.AuthResponse;
import com.example.backend.dto.LoginRequest;
import com.example.backend.dto.LoginResponse;
import com.example.backend.dto.RegisterRequest;
import com.example.backend.model.User;
import com.example.backend.repository.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UserRepository userRepository;
    private final BCryptPasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    // ⭐ 手写构造函数（解决你的编译错误）
    public AuthController(UserRepository userRepository,
                          BCryptPasswordEncoder passwordEncoder,
                          JwtUtil jwtUtil) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtUtil = jwtUtil;
    }

    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@RequestBody LoginRequest request) {
        return userRepository.findByEmail(request.email())
            .filter(user -> passwordEncoder.matches(request.password(), user.getPassword()))
            .map(user -> {
                String token = jwtUtil.generateToken(user);

                LoginResponse.UserFields userFields = new LoginResponse.UserFields(
                        user.getId(),
                        user.getFirstname(),
                        user.getLastname(),
                        user.getEmail()
                );

                return ResponseEntity.ok(new LoginResponse(token, userFields));
            })
            .orElseGet(() -> ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(null));
    }

    @PostMapping("/register")
    public ResponseEntity<AuthResponse> register(@RequestBody RegisterRequest request) {
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

        String token = jwtUtil.generateToken(user);

        AuthResponse.UserFields userFields = new AuthResponse.UserFields(
            savedUser.getId(),
            savedUser.getFirstname(),
            savedUser.getLastname(),
            savedUser.getEmail()
        );

        // ⭐ 返回 token + user
        AuthResponse response = new AuthResponse(token, userFields);

        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }
}
