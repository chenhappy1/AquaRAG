pipeline {
    // Allows this pipeline to run on any available Jenkins agent/node
    agent any

    environment {
        PROJECT_NAME = 'AquaRAG'
    }

    stages {
        // Stage 1: Pull the latest code from your GitHub repository
        stage('Checkout Source Code') {
            steps {
                echo "=== Starting to pull project: ${env.PROJECT_NAME} from GitHub ==="
                checkout scm
            }
        }

        // Stage 2: Install dependencies and compile the Angular 22 app
        stage('Build Angular Frontend') {
            steps {
                echo "=== Entering frontend directory for compilation ==="
                // The 'dir' block automatically runs commands inside your 'frontend' folder
                dir('frontend') {
                    echo "Installing Node modules (npm install)..."
                    sh 'npm install'
                    
                    echo "Building Angular project for production..."
                    // Standard production build command for Angular 22
                    sh 'npx ng build --configuration production'
                }
            }
        }

        // Stage 3: Deploy the compiled static assets
        stage('Deploy To Web Server') {
            steps {
                echo "=== Starting deployment ==="
                echo "Deploying the built static files to Nginx/Apache directory..."
                
                // Note: Angular 22 outputs production files to 'dist/[project-name]/browser/' by default.
                // This command copies them into the default Ubuntu web directory.
                sh 'sudo cp -r frontend/dist/AquaRAG/browser/* /var/www/html/'
                
                echo "Deployment finished successfully!"
            }
        }
    }

    // Post-actions executing based on the final pipeline status
    post {
        success {
            echo '🎉 Congratulations! Angular project built and deployed successfully!'
        }
        failure {
            echo '❌ Oh no, something went wrong during the build process. Please check the logs above.'
        }
    }
}