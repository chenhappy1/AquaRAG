pipeline {
    // Allows this pipeline to run on any available Jenkins agent/node
    agent any

    environment {
        PROJECT_NAME = 'AquaRAG'
        // Crucial flag to prevent Node.js from memory-crashing your AWS EC2 instance
        NODE_OPTIONS = '--max-old-space-size=512'
    }

    stages {
        // Stage 1: Pull fullstack source code from GitHub
        stage('Checkout Source Code') {
            steps {
                echo "=== 1. Pulling fullstack source code from GitHub ==="
                checkout scm
            }
        }

        // Stage 2: Install dependencies and compile Angular 22 Frontend
        stage('Build Angular Frontend') {
            steps {
                echo "=== 2. Compiling Angular Frontend ==="
                dir('frontend') {
                    echo "Installing Node modules..."
                    sh 'npm install --no-audit --no-fund'
                    echo "Building Angular production distribution..."
                    sh 'npx ng build --configuration production'
                }
            }
        }

        // Stage 3: Compile and package Java Spring Boot Backend (New)
        stage('Build Java Backend') {
            steps {
                echo "=== 3. Compiling Java Spring Boot Backend ==="
                // The 'dir' block shifts context into your new backend folder
                dir('backend') {
                    echo "Granting executable privileges to Maven Wrapper..."
                    sh 'chmod +x mvnw'
                    
                    echo "Packaging Spring Boot project into a JAR (Skipping tests for faster execution)..."
                    // Uses the embedded Maven wrapper to build without needing Maven installed globally
                    sh './mvnw clean package -DskipTests'
                }
            }
        }

        // Stage 4: Deploy both frontend and backend assets
        stage('Deploy Fullstack Application') {
            steps {
                echo "=== 4. Starting Fullstack Deployment ==="
                
                // --- Frontend Deployment ---
                echo "Cleaning old artifacts and copying new static assets to Nginx server path..."
                sh 'sudo rm -rf /var/www/html/*'
                sh 'sudo cp -r frontend/dist/frontend/browser/* /var/www/html/'
                
                // --- Backend Deployment Preparation ---
                echo "Verifying generated backend executable production JAR file..."
                // Confirms that the executable production .jar file exists inside the target directory
                sh 'ls -la backend/target/*.jar'
                
                echo "Fullstack deployment cycle completed successfully!"
            }
        }
    }

    // Post-actions executed based on the absolute compilation status
    post {
        success {
            echo '🎉 Congratulations! Both Angular and Spring Boot projects built successfully!'
        }
        failure {
            echo '❌ Fullstack deployment pipeline failed. Please inspect the log files above.'
        }
    }
}