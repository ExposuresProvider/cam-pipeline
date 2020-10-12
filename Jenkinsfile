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
                    sh "rm -rf gene-data"
                    sh "if [ ! -d gene-data ]; then mkdir gene-data; fi"
                    sh "cd gene-data; git clone https://github.com/geneontology/noctua-models; mv noctua-models noctua-models-dev; cd noctua-models-dev; git checkout dev"
                    sh "cd gene-data; git clone --depth 1 https://github.com/geneontology/noctua-models"
                    sh "make all"
             }
         }
         stage('Validation Reports') {
            steps {
                    sh 'make validate'
            }
         }
     }
 }
