pipeline {
    agent any

    environment {
        SONAR_HOST_URL = 'http://192.168.50.4:9000/'
        SONAR_AUTH_TOKEN = credentials('sonarqube')
        RECIPIENT_EMAIL = 'yahyakaddour5@gmail.com'
    }

    stages {
        stage('Checkout SCM') {
            steps {
                checkout scm
            }
        }

        stage('Static Code Analysis (Bandit + SonarQube)') {
            steps {
                script {
                    docker.image('python:3.11').inside('-u root') {
                        sh '''
                            pip install bandit
                            mkdir -p reports
                            bandit -r . -f html -o reports/bandit-report.html || true

                            # SonarQube scan
                            sonar-scanner \
                                -Dsonar.projectKey=PythonApp \
                                -Dsonar.sources=. \
                                -Dsonar.host.url=${SONAR_HOST_URL} \
                                -Dsonar.login=${SONAR_AUTH_TOKEN} \
                                -Dsonar.python.version=3.11 \
                                -Dsonar.projectName=PythonApp \
                                -Dsonar.projectVersion=1.0
                        '''
                    }
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    sh 'docker build -t bankapp .'
                }
            }
        }

        stage('Deploy and Run App') {
            steps {
                script {
                    sh '''
                        docker stop bankapp || true
                        docker rm bankapp || true
                        docker run -d --name bankapp -p 5000:5000 bankapp
                    '''
                }
            }
        }

        stage('Dynamic Analysis (OWASP ZAP)') {
            steps {
                script {
                    // Make sure OWASP ZAP is installed in Jenkins machine
                    sh '''
                        mkdir -p reports
                        zap-baseline.py -t http://localhost:5000 -r reports/owasp-zap-report.html || true
                    '''
                }
            }
        }
    }

    post {
        always {
            script {
                sh '''
                    docker stop bankapp || true
                    docker rm bankapp || true
                '''
            }
            archiveArtifacts artifacts: 'reports/*.html', allowEmptyArchive: true

            emailext (
                to: "${RECIPIENT_EMAIL}",
                subject: "Jenkins DevSecOps Pipeline - Build #${BUILD_NUMBER}",
                body: """
                <h3>DevSecOps Pipeline Execution Report</h3>
                <p>Status: ${currentBuild.currentResult}</p>
                <p>Project: ${JOB_NAME}</p>
                <p>Build Number: ${BUILD_NUMBER}</p>
                <p>Check attached reports (Bandit + OWASP ZAP).</p>
                """,
                attachmentsPattern: "reports/*.html",
                mimeType: 'text/html'
            )
        }
    }
}
