FROM openjdk:15-alpine as stage0
WORKDIR /opt/docker
COPY blazegraph.properties /1/opt/docker/
COPY biolink-local.ttl /1/opt/docker/
COPY chebi_mesh.tsv /1/opt/docker/
COPY create_uniprot_ncbi_rules.sc /1/opt/docker/
COPY Makefile /1/opt/docker/
COPY ontologies.ofn /1/opt/docker/
COPY sparql/ /1/opt/docker/sparql/
COPY ubergraph-axioms.ofn /1/opt/docker/
COPY uniprot-to-ncbi.txt /1/opt/docker/
COPY uniprot-to-ncbi-rules.ofn /1/opt/docker/
USER root
RUN ["chmod", "-R", "u=rwX,g=rwX", "/1/opt/docker"]

FROM openjdk:15-alpine as mainstage
USER root
RUN id -u cam 1>/dev/null 2>&1 || (( getent group 0 1>/dev/null 2>&1 || ( type groupadd 1>/dev/null 2>&1 && groupadd -g 0 root || addgroup -g 0 -S root )) && ( type useradd 1>/dev/null 2>&1 && useradd --system --create-home --uid 1001 --gid 0 cam || adduser -S -u 1001 -G root cam ))
WORKDIR /opt/docker
COPY --from=stage0 --chown=cam:root /1/opt/docker /opt/docker
ENV ROBOT_JAVA_ARGS="-Xmx24g -Xms24g"
ENV BLAZEGRAPH_RUNNER_JAVA_OPTS="-Xmx24g -Xms24g"
ENV NCIT_JAVA_OPTS="-Xmx24g -Xms24g"
ENV ROBOT_JAVA_OPTS="-Xmx24g -Xms24g"
ENV ARQ_JAVA_OPTS="-Xmx24g -Xms24g"
ENV PATH="$PATH:."

RUN apk update && apk add bash curl make coreutils tar git
RUN chown cam:root /opt/docker

USER 1001:0

RUN curl -L -O https://mirror.cogentco.com/pub/apache/jena/binaries/apache-jena-4.1.0.tar.gz && \
        tar -xzf apache-jena-4.1.0.tar.gz && \
        rm apache-jena-4.1.0.tar.gz && \
        ln -s ./apache-jena-4.1.0/bin/arq ./arq

RUN curl -L -O https://github.com/ontodev/robot/releases/download/v1.8.1/robot.jar && \
        curl -L -O https://raw.githubusercontent.com/ontodev/robot/v1.8.1/bin/robot && \
        chmod 755 robot

RUN curl -L -O https://github.com/balhoff/blazegraph-runner/releases/download/v1.6.4/blazegraph-runner-1.6.4.tgz && \
        tar -xzf blazegraph-runner-1.6.4.tgz && \
        rm blazegraph-runner-1.6.4.tgz && \
        ln -s ./blazegraph-runner-1.6.4/bin/blazegraph-runner./blazegraph-runner

RUN curl -L -O https://github.com/NCI-Thesaurus/ncit-utils/releases/download/v0.6/ncit-utils-0.6.tgz && \
        tar -xzf ncit-utils-0.6.tgz && \
        rm ncit-utils-0.6.tgz && \
        ln -s ./ncit-utils-0.6/bin/ncit-utils ./ncit-utils

RUN mkdir gene-data && git clone --depth 1 --filter=blob:none --sparse https://github.com/geneontology/noctua-models gene-data/noctua-models
RUN cd ./gene-data/noctua-models; git sparse-checkout set models; cd ../..

CMD []
