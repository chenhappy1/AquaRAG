# Stage 1: Build and package stage using Maven and Java 21
FROM maven:3-eclipse-temurin-25 AS build
WORKDIR /app
COPY . .

# Execute the packaging command and skip unit tests for speed
RUN mvn clean package -DskipTests

# Stage 2: Runtime stage to run the bundled lightweight application JAR
FROM eclipse-temurin:25-jre
WORKDIR /app

# Copy the compiled production executable JAR file from the build stage
COPY --from=build /app/target/*.jar app.jar

EXPOSE 9000
ENTRYPOINT ["java", "-jar", "app.jar"]