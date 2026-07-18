pipeline {
    agent any

    environment {
        PROJECT_NAME = 'AquaRAG'
        NODE_OPTIONS = '--max-old-space-size=512'
    }

    stages {
        stage('Checkout Source Code') {
            steps {
                echo "=== Starting to pull project: ${env.PROJECT_NAME} from GitHub ==="
                checkout scm
            }
        }

        stage('Build Angular Frontend') {
            steps {
                echo "=== Entering frontend directory ==="
                dir('frontend') {
                    echo "Installing Node modules with memory saving flags..."
                    sh 'npm install --no-audit --no-fund'
                    
                    echo "Building Angular project for production..."
                    sh 'npx ng build --configuration production'
                }
            }
        }

        stage('Deploy To Web Server') {
            steps {
                echo "=== Starting deployment ==="
                // Fixed path to match your exact Angular output location
                sh 'sudo cp -r frontend/dist/frontend/* /var/www/html/'
                echo "Deployment finished successfully!"
            }
        }
    }

    post {
        success {
            echo '🎉 Congratulations! Built and deployed successfully!'
        }
        failure {
            echo '❌ Build failed. Please inspect logs.'
        }
    }
}