FROM openjdk:8-alpine as stage0
WORKDIR /opt/docker
#COPY blazegraph.properties /1/opt/docker/
#COPY blazegraph-jar-2.1.4.jar /1/opt/docker/
#COPY cam-db-reasoned.jnl /1/opt/docker/
#COPY jetty-servlets-9.2.3.v20140905.jar /1/opt/docker/
COPY readonly_cors.xml /1/opt/docker/
USER root
RUN ["chmod", "-R", "u=rwX,g=rwX", "/1/opt/docker"]

FROM openjdk:8-alpine as mainstage
USER root
RUN id -u cam 1>/dev/null 2>&1 || (( getent group 0 1>/dev/null 2>&1 || ( type groupadd 1>/dev/null 2>&1 && groupadd -g 0 root || addgroup -g 0 -S root )) && ( type useradd 1>/dev/null 2>&1 && useradd --system --create-home --uid 1001 --gid 0 cam || adduser -S -u 1001 -G root cam ))
WORKDIR /opt/docker
COPY --from=stage0 --chown=cam:root /1/opt/docker /opt/docker
ENV JETTY_PORT="8666"
ENV JVM_OPTS="-Djava.awt.headless=true -server -Xmx32g -Xms32g -XX:MaxDirectMemorySize=3000m -XX:+UseG1GC"
ENV BLZG_HOME="/opt/docker/blazegraph"
ENV PATH="$PATH:$BLZG_HOME/bin:."

RUN apk update && apk add bash curl
RUN chown cam:root /opt/docker

USER 1001:0

RUN curl -L -O https://github.com/blazegraph/database/releases/download/BLAZEGRAPH_2_1_6_RC/blazegraph.tar.gz && \
        tar -xzf blazegraph.tar.gz && \
        rm blazegraph.tar.gz && \
        ln -s ./blazegraph-tgz-2.1.6-SNAPSHOT ./blazegraph

RUN mv -f readonly_cors.xml blazegraph/war/WEB-INF/override-web.xml
#RUN ln -s ./cam-db-reasoned.jnl ./blazegraph/data/blazegraph.jnl
CMD [ ]
#CMD blazegraph/bin/blazegraph.sh start
#CMD java -server -Xmx32g -Djetty.port=8666 -Djetty.overrideWebXml=readonly_cors.xml -cp blazegraph-jar-2.1.4.jar:jetty-servlets-9.2.3.v20140905.jar com.bigdata.rdf.sail.webapp.StandaloneNanoSparqlServer
