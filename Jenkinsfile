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
                    sh "rm -rf noctua-models-dev"
                    sh "rm -rf noctua-models"
                    sh "rm -rf gene-data"
                    sh "if [ ! -d gene-data ]; then mkdir gene-data; fi"
                    sh "cd gene-data; pwd;  git clone https://github.com/geneontology/noctua-models; mv noctua-models noctua-models-dev; cd noctua-models-dev; git checkout dev; cd ..; pwd"
                    sh "pwd; cd gene-data; pwd; git clone --depth 1 https://github.com/geneontology/noctua-models; pwd"
                    sh 'pwd; make -j 16 all'
             }
         }
//          stage('Validation Reports') {
//             steps {
//                     sh 'make -j 16 validate'
//             }
//          }
     }
 }
