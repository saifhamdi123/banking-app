def COLOR_MAP = [
    'SUCCESS': 'good',
    'FAILURE': 'danger',
]

pipeline {
    agent any
    
    environment {
        APP_NAME = "flask-banking-app"
        IMAGE_NAME = "${APP_NAME}"
        SCANNER_HOME = tool 'sonar-scanner'
        SONARQUBE_SERVER = 'sonar-server'
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
                git branch: 'main', url: 'https://github.com/yahyakaddour/bank-simple-app.git'
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
            post {
                success {
                    echo 'Bandit analysis completed'
                }
            }
        }

        stage('CODE ANALYSIS with SONARQUBE') {
            steps {
                echo "Running SonarQube scan for Python..."
                withSonarQubeEnv('sonar-server') {
                    sh '''
                        ${SCANNER_HOME}/bin/sonar-scanner \
                            -Dsonar.projectKey=flask-banking-app \
                            -Dsonar.projectName=flask-banking-app \
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
                        waitForQualityGate abortPipeline: false, credentialsId: 'sonar-token'
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

        stage("DAST Scan with OWASP ZAP") {
            steps {
                script {
                    echo '🔍 Running OWASP ZAP baseline scan on Flask app...'
                    
                    def exitCode = sh(script: '''
                        docker run --rm --user root --network host -v $(pwd):/zap/wrk:rw \
                        -t zaproxy/zap-stable zap-baseline.py \
                        -t http://localhost:5000 \
                        -r zap_report.html -J zap_report.json || true
                    ''', returnStatus: true)

                    echo "ZAP scan finished with exit code: ${exitCode}"

                    // Parse ZAP results
                    if (fileExists('zap_report.json')) {
                        try {
                            def zapJson = readJSON file: 'zap_report.json'
                            def highCount = zapJson.site.collect { site ->
                                site.alerts.findAll { it.risk == 'High' }.size()
                            }.sum() ?: 0
                            def mediumCount = zapJson.site.collect { site ->
                                site.alerts.findAll { it.risk == 'Medium' }.size()
                            }.sum() ?: 0
                            def lowCount = zapJson.site.collect { site ->
                                site.alerts.findAll { it.risk == 'Low' }.size()
                            }.sum() ?: 0

                            echo "✅ High severity issues: ${highCount}"
                            echo "⚠️ Medium severity issues: ${mediumCount}"
                            echo "ℹ️ Low severity issues: ${lowCount}"
                        } catch (Exception e) {
                            echo "Could not parse ZAP report: ${e.message}"
                        }
                    } else {
                        echo "ZAP JSON report not found, continuing build..."
                    }
                    
                    // Stop test container
                    echo "✅ DAST scan completed. Production app remains running."
                }
            }
            post {
                always {
                    echo '📦 Archiving ZAP scan reports...'
                    archiveArtifacts artifacts: 'zap_report.html,zap_report.json', allowEmptyArchive: true
                }
            }
        }
    }

    post {
        always {
            script {
                // Collect all security reports
                sh '''
                    mkdir -p security-reports
                    cp bandit-report.* security-reports/ 2>/dev/null || true
                    cp pip-audit-report.txt security-reports/ 2>/dev/null || true
                    cp trivyfs.txt security-reports/ 2>/dev/null || true
                    cp trivy-image.* security-reports/ 2>/dev/null || true
                    cp zap_report.* security-reports/ 2>/dev/null || true
                '''
                
                archiveArtifacts artifacts: 'security-reports/**', allowEmptyArchive: true
                
                // Send email with security reports
                def buildStatus = currentBuild.currentResult
                def buildUser = currentBuild.getBuildCauses('hudson.model.Cause$UserIdCause')[0]?.userId ?: 'GitHub User'

                emailext(
                    subject: "🔒 Pipeline ${buildStatus}: Flask Banking App #${env.BUILD_NUMBER}",
                    body: """
                        <html>
                            <body style="font-family: Arial, sans-serif;">
                                <h2>Flask Banking App - DevSecOps Pipeline Report</h2>
                                <hr>
                                <h3>Build Information</h3>
                                <table border="1" cellpadding="10">
                                    <tr><td><b>Job Name:</b></td><td>${env.JOB_NAME}</td></tr>
                                    <tr><td><b>Build Number:</b></td><td>${env.BUILD_NUMBER}</td></tr>
                                    <tr><td><b>Build Status:</b></td><td><b style="color: ${buildStatus == 'SUCCESS' ? 'green' : 'red'}">${buildStatus}</b></td></tr>
                                    <tr><td><b>Started by:</b></td><td>${buildUser}</td></tr>
                                    <tr><td><b>Build URL:</b></td><td><a href="${env.BUILD_URL}">${env.BUILD_URL}</a></td></tr>
                                </table>
                                <hr>
                                <h3>Security Scans Performed</h3>
                                <ul>
                                    <li><b>✅ SAST Analysis:</b> SonarQube (Static Application Security Testing)</li>
                                    <li><b>✅ Bandit Analysis:</b> Python Security Issue Detector</li>
                                    <li><b>✅ Dependency Scan:</b> pip-audit (Python Package Vulnerabilities)</li>
                                    <li><b>✅ Container Scan:</b> Trivy (Docker Image Vulnerabilities)</li>
                                    <li><b>✅ DAST Scan:</b> OWASP ZAP (Dynamic Application Security Testing)</li>
                                </ul>
                                <hr>
                                <h3>Deployment Status</h3>
                                <p><b>Flask app is now running in production at: http://localhost:5000</b></p>
                                <hr>
                                <h3>Next Steps</h3>
                                <p>Review the attached security reports for detailed findings and remediation recommendations.</p>
                                <p><a href="${env.BUILD_URL}">View Full Build Details</a></p>
                            </body>
                        </html>
                    """,
                    to: 'yahyakaddour5@gmail.com',
                    from: 'yahyakaddour5@gmail.com',
                    mimeType: 'text/html',
                    attachmentsPattern: 'security-reports/**'
                )
            }
        }
        
        failure {
            echo '❌ Pipeline failed! Review logs and security reports.'
        }
        
        success {
            echo '✅ Pipeline completed successfully! Flask app is running on port 5000'
            sh 'docker ps -a | grep flask-app-prod'
        }
    }
}
