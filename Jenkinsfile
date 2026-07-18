pipeline {
    agent any

    environment {
        // Define Docker Image tags for version control
        REGISTRY             = "localhost:5000" // Change this to your Docker Hub or AWS ECR if needed
        FRONTEND_IMAGE       = "aquarag-frontend:latest"
        PYTHON_BACKEND_IMAGE = "aquarag-backend-python:latest"
        JAVA_BACKEND_IMAGE   = "aquarag-backend-java:latest"
        
        // Containers runtime names
        FRONTEND_CONTAINER   = "aquarag-frontend"
        PYTHON_CONTAINER     = "aquarag-backend-python"
    }

    stages {
        stage('1. Checkout Source Code') {
            steps {
                echo 'Pulling the latest code from Git repository...'
                checkout scm
            }
        }

        stage('2. Build Python RAG Backend') {
            steps {
                echo 'Building Python FastAPI Docker Image...'
                // Navigates to the backend-python directory and builds using the new Dockerfile
                sh 'docker build -t ${PYTHON_BACKEND_IMAGE} ./backend-python'
            }
        }

        stage('3. Build Angular Frontend') {
            steps {
                echo 'Building Angular Frontend Docker Image...'
                // Navigates to the frontend directory and builds the user interface
                sh 'docker build -t ${FRONTEND_IMAGE} ./frontend'
            }
        }
        
        /* 
        OPTIONAL STAGE: Uncomment this block if you ever want Jenkins to build your Java Backend too.
        stage('Optional: Build Java Backend') {
            steps {
                echo 'Building original Java backend service...'
                sh 'docker build -t ${JAVA_BACKEND_IMAGE} ./backend'
            }
        }
        */

        stage('4. Deploy Application via Standard Docker') { 
            steps { 
                echo 'Deploying services using standard docker run commands...' 
                
                // 1. Stop and remove existing containers to prevent naming or port conflicts
                sh 'docker stop aquarag-backend-python aquarag-frontend || true'
                sh 'docker rm aquarag-backend-python aquarag-frontend || true'
                
                // 2. Run the Python Backend container (maps port 8000)
                sh 'docker run -d --name aquarag-backend-python -p 8000:8000 aquarag-backend-python:latest'
                
                // 3. Run the Angular Frontend container (maps port 80)
                sh 'docker run -d --name aquarag-frontend -p 80:80 aquarag-frontend:latest'
                
                echo 'Deployment successful! AquaRAG is running.' 
            } 
        } 


    }

    post {
        success {
            echo '🎉 Jenkins Pipeline finished successfully! AquaRAG is up and running.'
        }
        failure {
            echo '❌ Jenkins Pipeline failed. Please check the console logs above for errors.'
        }
    }
}