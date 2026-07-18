# 1. 编译构建阶段：使用 Java 25 新版镜像
FROM maven:3-eclipse-temurin-21 AS build
WORKDIR /app
COPY . .
# 执行打包命令，跳过测试
RUN mvn clean package -DskipTests

# 2. 运行阶段：仅复制打包好的 JAR 包运行，保持镜像体积轻量
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
EXPOSE 9000
ENTRYPOINT ["java", "-jar", "app.jar"]