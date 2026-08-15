package com.example.backend.repository;

import com.example.backend.model.User;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserRepository extends JpaRepository<User, UUID> {

    Optional<User> findByEmail(String email);

    Optional<User> findByFirstnameAndLastname(String firstname, String lastname);

    boolean existsByFirstnameAndLastname(String firstname, String lastname);

    boolean existsByEmail(String email);
}
