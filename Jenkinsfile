pipeline {
    agent {
        docker {
            image 'phenoscape/pipeline-tools:v1.3.1'
            label 'zeppo'
        }
    }
     stages {
         stage('Build') {
             steps {
                    sh "env"
                    sh "pwd"
                    sh "ls -AlF"
                    sh 'make -j 16 all'
             }
         }
         stage('Validation Reports') {
            steps {
                    sh 'make -j 16 validate'
            }
         }
     }
 }
