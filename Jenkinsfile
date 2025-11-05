pipeline {
  agent any

  environment {
    SONARQUBE = 'SonarQubeServer'
    APP_NAME = 'bank-simple-app'
    IMAGE_NAME = "bank-app:latest"
  }

  triggers {
    githubPush()
  }

  stages {
    stage('Checkout') {
      steps {
        git branch: 'main', url: 'https://github.com/yahyakaddour/bank-simple-app.git'
      }
    }

    stage('Static Code Analysis (Bandit + SonarQube)') {
      agent {
        docker { image 'python:3.11' }
      }
      steps {
        sh '''
          pip install bandit
          mkdir -p reports
          bandit -r . -f html -o reports/bandit-report.html
        '''
        withSonarQubeEnv("${SONARQUBE}") {
          sh 'sonar-scanner -Dsonar.projectKey=bank-app -Dsonar.sources=.'
        }
      }
    }

    stage('Build Docker Image') {
      steps {
        sh 'docker build -t $IMAGE_NAME .'
      }
    }

    stage('Deploy and Run App') {
      steps {
        sh 'docker run -d -p 5000:5000 --name bankapp $IMAGE_NAME'
      }
    }

    stage('Dynamic Analysis (OWASP ZAP)') {
      steps {
        sh '''
          mkdir -p reports
          zap.sh -cmd -quickurl http://localhost:5000 -quickout reports/zap-report.html
        '''
      }
    }
  }

  post {
    always {
      sh 'docker stop bankapp || true'
      sh 'docker rm bankapp || true'

      archiveArtifacts artifacts: 'reports/*.html', fingerprint: true

      emailext (
        subject: "DevSecOps Pipeline: ${currentBuild.currentResult}",
        body: "Pipeline finished with status: ${currentBuild.currentResult}. Reports attached.",
        to: "your-email@example.com",
        attachmentsPattern: "reports/*.html"
      )
    }
  }
}
