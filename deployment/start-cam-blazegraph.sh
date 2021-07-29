#!/bin/bash

java -server -Xmx32G -Dfile.encoding=UTF-8 -Djetty.port=8666 -Djetty.overrideWebXml=./readonly_cors.xml -Dbigdata.propertyFile=blazegraph.properties -cp blazegraph-jar-2.1.4.jar:jetty-servlets-9.2.3.v20140905.jar com.bigdata.rdf.sail.webapp.StandaloneNanoSparqlServer
