package com.example.backend.config;

import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.authentication.builders.AuthenticationManagerBuilder;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public BCryptPasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    // 声明 AuthenticationManager，禁止 Spring Boot 创建默认用户和抛出幽灵密码
    @Bean
    public AuthenticationManager authenticationManager(HttpSecurity http) throws Exception {
        return http.getSharedObject(AuthenticationManagerBuilder.class).build();
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .cors(Customizer.withDefaults())
            .csrf(csrf -> csrf.disable())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))

            // 禁用所有默认表单认证方式，防止被底层过滤器链强行挂起
            .httpBasic(httpBasic -> httpBasic.disable())
            .formLogin(formLogin -> formLogin.disable())
            .logout(logout -> logout.disable())

            // 必须允许匿名用户自由通行，确保登录和注册握手能够安全落地
            .anonymous(Customizer.withDefaults())

            .authorizeHttpRequests(auth -> auth
                // 🟢 极度关键：无条件放行所有浏览器的 OPTIONS 跨域预检流量，彻底杜绝 Preflight 403 恶疾！
                .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()

                // 统一放行认证网关路由，支持 K8s Ingress 掐头去尾后的多级路径匹配
                .requestMatchers("/api/auth/**", "/auth/**", "/login/**", "/register/**", "/**").permitAll()

                .anyRequest().authenticated()
            );

        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();
        
        // 🟢 黄金对齐：精确指定放行的域名与端口。绝不用通配符 *，完美适配 AllowCredentials 规则！
        config.setAllowedOrigins(List.of(
            "http://localhost",       // 💡 核心：允许外界通过本地 K8s Ingress 网关（80端口）跨域访问
            "http://localhost:4200",  // 允许前端 Angular 源码本地开发环境调试访问
            "http://18.191.193.40"    // 允许线上 AWS 生产环境实例实例 IP 访问
        ));
        
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        config.setAllowedHeaders(List.of("*"));
        config.setAllowCredentials(true); // 开启凭证支持，与上面的显式域名清单实现完美无缝握手

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }
}