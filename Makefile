JAVA_ENV=JAVA_OPTS="-Xmx96G -XX:+UseParallelGC"
BLAZEGRAPH-RUNNER=$(JAVA_ENV) blazegraph-runner

ROBOT_ENV=ROBOT_JAVA_ARGS="-Xmx96G -XX:+UseParallelGC"
ROBOT=$(ROBOT_ENV) robot

JVM_ARGS=JVM_ARGS="-Xmx96G -XX:+UseParallelGC"
ARQ=$(JVM_ARGS) arq

SCALA_RUN=$(JAVA_ENV) COURSIER_CACHE=/workspace/coursier-cache scala-cli run --server=false

BIOLINK=v4.2.1

# Phony targets
.PHONY: all

all: kg.tsv
	echo All done.

owlrl-datalog:
	git clone https://github.com/balhoff/owlrl-datalog.git

owlrl-datalog/bin/owl_rl_abox_quads: owlrl-datalog owlrl-datalog/src/datalog/swrl.dl
	cd owlrl-datalog &&\
	mkdir -p bin &&\
	souffle -c src/datalog/owl_rl_abox_quads.dl -o bin/owl_rl_abox_quads

owlrl-datalog/src/datalog/swrl.dl: ontologies-merged.ttl owlrl-datalog
	$(SCALA_RUN) owlrl-datalog/src/scala/swrl-to-souffle.sc -- ontologies-merged.ttl $@

owlrl-datalog/bin/owl_from_rdf: owlrl-datalog
	cd owlrl-datalog &&\
	mkdir -p bin &&\
	souffle -c src/datalog/owl_from_rdf.dl -o bin/owl_from_rdf

scripts/kg_edges: scripts/kg_edges.dl
	souffle -c $< -o $@

# Step 3. Convert ontologies-merged.ttl into a format that can be read by Souffle.
# RIOT is a Jena tool that converts Turtle into n-Triples using streaming, and
# turn it into a TSV with three columns (?s ?p ?o).
ontology.facts: ontologies-merged.ttl
	riot --nocheck --output=ntriples $< | sed 's/ /\t/' | sed 's/ /\t/' | sed 's/ \.$$//' >$@

# Step 4. owl_from_rdf converts RDF triples (in TSV) into OWL data structures.
ontology.dir: owlrl-datalog/bin/owl_from_rdf ontology.facts
	mkdir -p ontology && ./owlrl-datalog/bin/owl_from_rdf -D ontology && touch $@

# Step 1. Import all the ontologies in ontologies.ofn into the `mirror/` directory.
# Also writes out a catalog file which will be used in future Robot.
# TODO: replace with the ontology.dir pattern of creating a directory and then touching mirror.dir
mirror: ontologies.ofn
	rm -rf $@ &&\
	$(ROBOT) mirror -i $< -d $@ -o $@/catalog-v001.xml

# Step 2. Create ontologies-merged.ttl by merging the ontologies in mirror with the Ubergraph axioms.
# Unsatisfiable classes are dumped into the debug file (debug.ofn), which is not created if there are
# no problems.
#FIXME stop disabling disjoint checks
ontologies-merged.ttl: ontologies.ofn ubergraph-axioms.ofn mirror
	$(ROBOT) merge --catalog mirror/catalog-v001.xml --include-annotations true \
	-i $< -i ubergraph-axioms.ofn \
	remove --axioms 'disjoint' --trim true --preserve-structure false \
	remove --term 'owl:Nothing' --trim true --preserve-structure false \
	remove --term 'http://purl.obolibrary.org/obo/caro#part_of' --term 'http://purl.obolibrary.org/obo/caro#develops_from' --trim true --preserve-structure false \
	reason -r ELK -D debug.ofn -o $@

# Step 5. Download all the Noctua models.
noctua-models.dir:
	git clone --depth 1 https://github.com/geneontology/noctua-models && touch $@

aop-models.dir:
	git clone --depth 1 https://github.com/ExposuresProvider/noctua-models.git aop-models && touch $@

# Step 6. Merge all the Noctua models. For each model:
# 	- Loads the model.
#	- Identifies the ontology IRI.
#	- Filters out non-production/non-Reactome models.
#	- Outputs nquads where the graph is the ontology IRI.
noctua-models.nq: noctua-models.dir scripts/merge_noctua_models.sc
	$(SCALA_RUN) scripts/merge_noctua_models.sc -- noctua-models/models $@

aop-models.nq: aop-models.dir scripts/merge_noctua_models.sc
	$(SCALA_RUN) scripts/merge_noctua_models.sc -- aop-models/models $@

# Step 7. Prepare the Signor models.
# TODO: replace with a Scala script similar to the one for noctua-models.nq.
signor-models.nq: signor-models
	rm -f $@.jnl &&\
	$(BLAZEGRAPH-RUNNER) load --journal=$@.jnl --properties=blazegraph.properties --informat=turtle --use-ontology-graph=true signor-models &&\
	$(BLAZEGRAPH-RUNNER) update --journal=$@.jnl --properties=blazegraph.properties sparql/set-provenance-to-signor.ru &&\
	$(BLAZEGRAPH-RUNNER) dump --journal=$@.jnl --properties=blazegraph.properties --outformat=n-quads $@ && rm $@.jnl

# Step 8. Download CTD file.
CTD_chem_gene_ixns_structured.xml:
	curl -L -O 'http://ctdbase.org/reports/CTD_chem_gene_ixns_structured.xml.gz' &&\
	gunzip CTD_chem_gene_ixns_structured.xml.gz

# Step 9. Generate an n-quads file from CTD.
# (ctd-to-owl is in the Docker container that we use).
ctd-models.nq: CTD_chem_gene_ixns_structured.xml
	$(JAVA_ENV) ctd-to-owl CTD_chem_gene_ixns_structured.xml $@ chebi_mesh.tsv

# Step 10. Concatenate all RDF files using a single RIOT instance (to make sure blank nodes don't collapse)
# to create quad.facts. Each quad has a graph IRI that tells you were the quad came from.
# Must concatenate multiple RDF files using riot before loading into Souffle, so that blank nodes don't collide
quad.facts: noctua-models.nq aop-models.nq ctd-models.nq
	riot -q --output=N-Quads $^ | sed 's/ /\t/' | sed 's/ /\t/' | sed -E 's/\t(.+) (.+) \.$$/\t\1\t\2/' >$@

# Step 11. Reason over the quad.facts, which:
# - 1. Load the ontology from ontology.dir
# - 2. Read asserted triples from quad.facts
# - 3. Create inferred graphs for every asserted graph, adding insertions.
#
# This uses a bunch of rules:
# - All the OWL RL rules (but with graphs to prevent inferencing between graphs).
# 	(Note that ontology-related rules will use triples but data-related rules will use quads.)
#
# Note that the output file -- inferred.csv -- is actually a TSV file.
inferred.csv: quad.facts ontology.dir owlrl-datalog/bin/owl_rl_abox_quads
	./owlrl-datalog/bin/owl_rl_abox_quads

# Step 12. Download the Biolink model.
biolink-model.owl.ttl:
	curl -L -O 'https://raw.githubusercontent.com/biolink/biolink-model/$(BIOLINK)/project/owl/biolink_model.owl.ttl'

# Step 13. Convert Biolink model into an n-triples file.
biolink.facts: biolink-model.owl.ttl
	riot -q --syntax=turtle --output=ntriples $< | sed 's/ /\t/' | sed 's/ /\t/' | sed 's/ \.$$//' >$@

# Step 14. Download the Biolink Model prefix map.
biolink-model-prefix-map.json:
	curl -L -O 'https://raw.githubusercontent.com/biolink/biolink-model/$(BIOLINK)/project/prefixmap/biolink_model_prefix_map.json'

# Step 15. Load all the data and ontologies.
# - ./scripts/kg_edges: compiled from ./scripts/kg_edges.dl with Souffle (see above).
# - inferred.csv: All inferred quads.
# - quad.facts: All asserted quads.
# - biolink.facts: Biolink model.
# - ontology.facts: only used to convert REACTOME identifiers into UniProtKB identifiers.
# - Also uses: ro-to-biolink-local-mappings.tsv to map from RO to Biolink.
#	- TODO: add as a prereq
# Creates a TSV file named kg_edge.csv with five columns:
# - subj: direct type of subject
# - pred: Biolink predicate
# - obj: direct type of object
# - ps: primary_source
# - prov: graph that this is coming from (without brackets -- if it had brackets, it would
#   be ignored by scripts/compact_iris.sc)
kg_edge.csv: scripts/kg_edges inferred.csv quad.facts biolink.facts ontology.facts
	./scripts/kg_edges

# Step 16. Compact IRIs in the kg_edge.csv file using the specified prefixes.
kg.tsv: kg_edge.csv scripts/compact_iris.sc biolink-model-prefix-map.json supplemental-namespaces.json
	$(SCALA_RUN) scripts/compact_iris.sc --  biolink-model-prefix-map.json supplemental-namespaces.json kg_edge.csv $@
