pipeline {
    agent {
        docker {
            image 'renciorg/cam-pipeline-tools:v1.3'
            label 'zeppo'
        }
    }
     stages {
         stage('Build') {
             steps {
                    sh "env"
                    sh "pwd"
                    sh "ls -AlF"
                    sh "make clean"
                    sh "if [ ! -d gene-data ]; then mkdir gene-data; fi"
                    sh "cd gene-data; git clone --depth 1 https://github.com/geneontology/noctua-models"
                    sh "make ctd-models-inferences.nq all"
             }
         }
         stage('Validation Reports') {
            steps {
                    sh 'make validate'
            }
         }
     }
 }
