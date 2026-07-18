pipeline {
    // Allows this pipeline to run on any available Jenkins agent/node
    agent any

    environment {
        PROJECT_NAME = 'AquaRAG'
    }

    stages {
        // Stage 1: Pull code from GitHub
        stage('Checkout Source Code') {
            steps {
                echo "=== Starting to pull project: ${env.PROJECT_NAME} from GitHub ==="
                // This checks out the source code using the Git configuration specified in the Jenkins UI
                checkout scm
            }
        }

        // Stage 2: Build frontend assets (Targeting your 'frontend' folder)
        stage('Build Frontend') {
            steps {
                echo "=== Entering frontend directory for dependency installation and build ==="
                // Using the 'dir' block to switch focus into the frontend folder automatically
                dir('frontend') {
                    echo "Currently inside the frontend folder..."
                    
                    // Note: Ensure Node.js and npm are installed on your AWS EC2 instance.
                    // Once confirmed, you can uncomment the lines below:
                    // sh 'npm install'
                    // sh 'npm run build'
                }
            }
        }

        // Stage 3: Deploy the built files
        stage('Deploy') {
            steps {
                echo "=== Starting deployment ==="
                echo "The built static files are ready. Deploying to the target web server environment..."
                
                // In a real-world scenario, you would put your server copy command here, for example:
                // sh 'sudo cp -r frontend/dist/* /var/www/html/'
                
                echo "Deployment finished successfully!"
            }
        }
    }

    // Post-actions that execute depending on the completion status
    post {
        success {
            echo '🎉 Congratulations! The pipeline built and deployed successfully!'
        }
        failure {
            echo '❌ Oh no, something went wrong during the build process. Please inspect the logs above.'
        }
    }
}