JAVA_ENV=JAVA_OPTS="-Xmx96G -XX:+UseParallelGC"
BLAZEGRAPH-RUNNER=$(JAVA_ENV) blazegraph-runner

ROBOT_ENV=ROBOT_JAVA_ARGS="-Xmx96G -XX:+UseParallelGC"
ROBOT=$(ROBOT_ENV) robot

JVM_ARGS=JVM_ARGS="-Xmx96G -XX:+UseParallelGC"
ARQ=$(JVM_ARGS) arq

SCALA_RUN=$(JAVA_ENV) COURSIER_CACHE=/home/cam/coursier-cache scala-cli run

BIOLINK=v3.2.5

owlrl-datalog:
	git clone https://github.com/balhoff/owlrl-datalog.git

#FIXME commit change for prov:wasDerivedFrom
owlrl-datalog/bin/owl_rl_abox_quads: owlrl-datalog owlrl-datalog/src/datalog/swrl.dl
	cd owlrl-datalog &&\
	mkdir -p bin &&\
	souffle -c src/datalog/owl_rl_abox_quads.dl -o bin/owl_rl_abox_quads

#owlrl-datalog/src/datalog/swrl.dl: swrl.dl
#	cp swrl.dl $@

owlrl-datalog/src/datalog/swrl.dl: ontologies-merged.ttl owlrl-datalog
	$(SCALA_RUN) owlrl-datalog/src/scala/swrl-to-souffle.sc -- ontologies-merged.ttl $@

owlrl-datalog/bin/owl_from_rdf: owlrl-datalog
	cd owlrl-datalog &&\
	mkdir -p bin &&\
	souffle -c src/datalog/owl_from_rdf.dl -o bin/owl_from_rdf

scripts/kg_edges: scripts/kg_edges.dl
	souffle -c $< -o $@

ontology.facts: ontologies-merged.ttl
	riot --nocheck --output=ntriples $< | sed 's/ /\t/' | sed 's/ /\t/' | sed 's/ \.$$//' >$@

ontology.dir: owlrl-datalog/bin/owl_from_rdf ontology.facts
	mkdir -p ontology && ./owlrl-datalog/bin/owl_from_rdf -D ontology && touch $@

mirror: ontologies.ofn
	rm -rf $@ &&\
	$(ROBOT) mirror -i $< -d $@ -o $@/catalog-v001.xml

#FIXME stop disabling disjoint checks
ontologies-merged.ttl: ontologies.ofn ubergraph-axioms.ofn mirror
	$(ROBOT) merge --catalog mirror/catalog-v001.xml --include-annotations true \
	-i $< -i ubergraph-axioms.ofn \
	remove --axioms 'disjoint' --trim true --preserve-structure false \
	remove --term 'owl:Nothing' --trim true --preserve-structure false \
	remove --term 'http://purl.obolibrary.org/obo/caro#part_of' --term 'http://purl.obolibrary.org/obo/caro#develops_from' --trim true --preserve-structure false \
	reason -r ELK -D debug.ofn -o $@

noctua-models.dir:
	git clone --depth 1 https://github.com/geneontology/noctua-models && touch $@

noctua-models.nq: noctua-models.dir
	rm -f $@.jnl &&\
	$(BLAZEGRAPH-RUNNER) load --journal=$@.jnl --properties=blazegraph.properties --informat=turtle --use-ontology-graph=true noctua-models/models &&\
	$(BLAZEGRAPH-RUNNER) update --journal=$@.jnl --properties=blazegraph.properties sparql/delete-non-production-models.ru &&\
	$(BLAZEGRAPH-RUNNER) dump --journal=$@.jnl --properties=blazegraph.properties --outformat=n-quads $@ && rm $@.jnl

signor-models.nq: signor-models
	rm -f $@.jnl &&\
	$(BLAZEGRAPH-RUNNER) load --journal=$@.jnl --properties=blazegraph.properties --informat=turtle --use-ontology-graph=true signor-models &&\
	$(BLAZEGRAPH-RUNNER) update --journal=$@.jnl --properties=blazegraph.properties sparql/set-provenance-to-signor.ru &&\
	$(BLAZEGRAPH-RUNNER) dump --journal=$@.jnl --properties=blazegraph.properties --outformat=n-quads $@ && rm $@.jnl

CTD_chem_gene_ixns_structured.xml:
	curl -L -O 'http://ctdbase.org/reports/CTD_chem_gene_ixns_structured.xml.gz' &&\
	gunzip CTD_chem_gene_ixns_structured.xml.gz

ctd-models.nq: CTD_chem_gene_ixns_structured.xml
	$(JAVA_ENV) ctd-to-owl CTD_chem_gene_ixns_structured.xml $@ chebi_mesh.tsv

# Must concatenate multiple RDF files using riot before loading into Souffle, so that blank nodes don't collide
quad.facts: noctua-models.nq ctd-models.nq
	riot -q --output=N-Quads noctua-models.nq ctd-models.nq | sed 's/ /\t/' | sed 's/ /\t/' | sed -E 's/\t(.+) (.+) \.$$/\t\1\t\2/' >$@

inferred.csv: quad.facts ontology.dir owlrl-datalog/bin/owl_rl_abox_quads
	./owlrl-datalog/bin/owl_rl_abox_quads

biolink-model.owl.ttl:
	curl -L -O 'https://raw.githubusercontent.com/biolink/biolink-model/$(BIOLINK)/biolink-model.owl.ttl'

biolink.facts: biolink-model.owl.ttl
	riot -q --syntax=turtle --output=ntriples $< | sed 's/ /\t/' | sed 's/ /\t/' | sed 's/ \.$$//' >$@

biolink-model-prefix-map.json:
	curl -L -O 'https://raw.githubusercontent.com/biolink/biolink-model/$(BIOLINK)/prefix-map/biolink-model-prefix-map.json'

kg_edge.csv: scripts/kg_edges inferred.csv quad.facts biolink.facts ontology.facts
	./scripts/kg_edges

kg.tsv: kg_edge.csv scripts/compact_iris.sc biolink-model-prefix-map.json supplemental-namespaces.json
	$(SCALA_RUN) scripts/compact_iris.sc --  biolink-model-prefix-map.json supplemental-namespaces.json kg_edge.csv $@
