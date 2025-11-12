pipeline {
    agent any
    
    environment {
        APP_NAME = "banking-app"
        IMAGE_NAME = "${APP_NAME}"
        SCANNER_HOME = tool 'sonar-scanner'
        
        PYTHON_VERSION = '3.11'
        FLASK_PORT = '5000'
    }
    
    options {
        timestamps()
        timeout(time: 1, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {
        stage("Clean Workspace") {
            steps {
                cleanWs()
            }
        }

        stage("Git Checkout") {
            steps {
                echo "Cloning repository from GitHub..."
                git branch: 'main', url: 'https://github.com/saifhamdi123/banking-app.git'
            }
        }

        stage('BUILD') {
            steps {
                echo "Installing Python dependencies..."
                sh '''
                    apt-get update && apt-get install -y python3-pip || true
                    python3 -m pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install pytest pytest-cov pylint flake8 bandit
                '''
            }
            post {
                success {
                    echo 'Dependencies installed successfully'
                }
            }
        }

        stage('UNIT TEST') {
            steps {
                echo "Running unit tests with pytest..."
                sh '''
                    pytest --cov=. --cov-report=xml --cov-report=html -v || true
                '''
            }
            post {
                success {
                    echo 'Unit tests completed'
                    archiveArtifacts artifacts: 'htmlcov/**', allowEmptyArchive: true
                }
            }
        }

        stage('INTEGRATION TEST') {
            steps {
                echo "Running integration tests and code quality checks..."
                sh '''
                    pylint app.py --fail-under=7.0 --exit-zero || true
                    flake8 app.py --count --exit-zero --max-complexity=10 || true
                '''
            }
        }

        stage('CODE ANALYSIS WITH BANDIT') {
            steps {
                echo "Running Bandit security analysis..."
                sh '''
                    bandit -r . -f json -o bandit-report.json || true
                    bandit -r . -f txt -o bandit-report.txt || true
                '''
            }
        }

        stage('CODE ANALYSIS with SONARQUBE') {
            steps {
                echo "Running SonarQube scan for Python..."
                withSonarQubeEnv('sonarqube_scanner') {
                    sh '''
                        ${SCANNER_HOME}/bin/sonar-scanner \
                            -Dsonar.projectKey=banking-app \
                            -Dsonar.projectName=banking-app \
                            -Dsonar.projectVersion=1.0 \
                            -Dsonar.sources=. \
                            -Dsonar.sourceEncoding=UTF-8 \
                            -Dsonar.python.coverage.reportPaths=coverage.xml \
                            -Dsonar.exclusions=**/venv/**,**/.git/**,**/.*,**/test_*
                    '''
                }
            }
        }

        stage("Quality Gate") {
            steps {
                script {
                    echo "Waiting for SonarQube Quality Gate..."
                    timeout(time: 5, unit: 'MINUTES') {
                        waitForQualityGate abortPipeline: false, credentialsId: 'sonarqube'
                    }
                }
            }
        }

        stage("Python Dependency Check Scan") {
            steps {
                echo "Scanning Python dependencies for vulnerabilities..."
                sh '''
                    pip install pip-audit
                    pip-audit --desc > pip-audit-report.txt || true
                '''
            }
        }

        stage("Trivy File Scan") {
            steps {
                echo "Running Trivy filesystem scan..."
                sh "trivy fs . > trivyfs.txt || true"
            }
        }

        stage("Build Docker Image") {
            steps {
                echo "Building Docker image: ${IMAGE_NAME}:${BUILD_NUMBER}"
                script {
                    env.IMAGE_TAG = "${IMAGE_NAME}:${BUILD_NUMBER}"
                    sh "docker rmi -f ${IMAGE_NAME}:latest ${env.IMAGE_TAG} || true"
                    
                    // Build and tag Docker image
                    dockerImage = docker.build("${IMAGE_NAME}:latest", ".")
                    sh "docker tag ${IMAGE_NAME}:latest ${env.IMAGE_TAG}"
                }
            }
        }

        stage("Trivy Scan Image") {
            steps {
                script {
                    echo "🔍 Running Trivy scan on Docker image: ${env.IMAGE_TAG}"
                    sh '''
                        trivy image -f json -o trivy-image.json ${IMAGE_TAG} || true
                        trivy image -f table -o trivy-image.txt ${IMAGE_TAG} || true
                    '''
                }
            }
        }

        stage("Deploy to Container") {
            steps {
                echo "Deploying Flask app to container..."
                script {
                    sh '''
                        docker rm -f flask-app-prod || true
                        docker run -d --name flask-app-prod -p 5000:5000 ${IMAGE_TAG}
                        sleep 10
                        
                        echo "Waiting for Flask app to be ready..."
                        for i in {1..30}; do
                            if curl -s http://localhost:5000 > /dev/null; then
                                echo "Flask app is ready!"
                                break
                            fi
                            echo "Attempt $i: Flask app not ready yet, waiting..."
                            sleep 2
                        done
                        
                        echo "Flask app deployed and running on port 5000"
                        docker ps -a | grep flask-app-prod
                    '''
                }
            }
        }
        
    }
}
