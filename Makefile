# set JAVA_OPTS=-Xmx64G before running make for blazegraph-runner, ctd-to-owl, ncit-utils
JAVA_ENV=JAVA_OPTS=-Xmx120G
BLAZEGRAPH-RUNNER=$(JAVA_ENV) blazegraph-runner
NCIT-UTILS=$(JAVA_ENV) ncit-utils

# set ROBOT_JAVA_ARGS=-Xmx64G before running make for robot
ROBOT_ENV=ROBOT_JAVA_ARGS=-Xmx120G
ROBOT=$(ROBOT_ENV) robot

JVM_ARGS=JVM_ARGS=-Xmx120G
ARQ=$(JVM_ARGS) arq

# git clone git@github.com:geneontology/noctua-models.git
NOCTUA_MODELS_REPO=gene-data/noctua-models
BIOLINK=2.0.2

.PHONY: clean validate

clean:
	rm -rf gene-data

## Generate validation reports from sparql queries
validate: missing-biolink-terms.ttl missing-biolink-relation.ttl

missing-biolink-terms.ttl: sparql/reports/owl-missing-biolink-term.rq cam-db-reasoned.jnl
	$(BLAZEGRAPH-RUNNER) select --journal=cam-db-reasoned.jnl --properties=blazegraph.properties --outformat=TSV $< $@

missing-biolink-relation.ttl: sparql/reports/owl-missing-biolink-relation.rq cam-db-reasoned.jnl
	$(BLAZEGRAPH-RUNNER) select --journal=cam-db-reasoned.jnl --properties=blazegraph.properties --outformat=TSV $< $@

all: cam-db-reasoned.jnl

noctua-models.jnl: $(NOCTUA_MODELS_REPO)/models/*.ttl
	$(BLAZEGRAPH-RUNNER) load --journal=$@ --properties=blazegraph.properties --informat=turtle --use-ontology-graph=true $(NOCTUA_MODELS_REPO)/models &&\
	$(BLAZEGRAPH-RUNNER) update --journal=$@ --properties=blazegraph.properties sparql/delete-non-production-models.ru

CTD_chem_gene_ixns_structured.xml:
	curl -L -O 'http://ctdbase.org/reports/CTD_chem_gene_ixns_structured.xml.gz' &&\
	gunzip CTD_chem_gene_ixns_structured.xml.gz

noctua-reactome-ctd-models.jnl: noctua-models.jnl #CTD_chem_gene_ixns_structured.xml chebi_mesh.tsv
	cp $< $@ #&&\
	# Temporarily disable CTD ingestion to allow more rapid turnaround while the full KP is developed
	#ctd-to-owl CTD_chem_gene_ixns_structured.xml $@ blazegraph.properties chebi_mesh.tsv

cam-db-reasoned.jnl: noctua-reactome-ctd-models-ubergraph.jnl
	cp $< $@ &&\
	$(BLAZEGRAPH-RUNNER) reason --journal=$@ --properties=blazegraph.properties --reasoner=whelk --append-graph-name='#inferred' --ontology='http://reasoner.renci.org/ontology' --source-graphs-query=sparql/find-asserted-models.rq --direct-types=true

ncbi-gene-classes.ttl: uniprot-to-ncbi-rules.ofn
	$(ROBOT) query --input uniprot-to-ncbi-rules.ofn --query sparql/construct-ncbi-gene-classes.rq ncbi-gene-classes.ttl

protein-subclasses.ttl: noctua-reactome-ctd-models.jnl sparql/construct-protein-subclasses.rq
	$(BLAZEGRAPH-RUNNER) construct --journal=$< --properties=blazegraph.properties --outformat=turtle sparql/construct-protein-subclasses.rq $@

mesh-chebi-links.ttl: noctua-reactome-ctd-models.jnl
	$(BLAZEGRAPH-RUNNER) construct --journal=$< --properties=blazegraph.properties --outformat=turtle sparql/construct-mesh-chebi-links.rq $@

mirror: ontologies.ofn
	rm -rf $@ &&\
	$(ROBOT) mirror -i $< -d $@ -o $@/catalog-v001.xml

reacto-uniprot-rules.ttl: mirror
	$(ARQ) -q --data=mirror/purl.obolibrary.org/obo/go/extensions/reacto.owl --query=sparql/construct-reacto-uniprot-rules.rq --results=ttl >$@

biolink-class-hierarchy.ttl: biolink-model.ttl
	$(ARQ) -q --data=$< --query=sparql/construct-biolink-class-hierachy.rq --results=ttl >$@

ont-biolink-subclasses.ttl: biolink-model.ttl biolink-local.ttl
	$(ARQ) -q --data=biolink-model.ttl --data=biolink-local.ttl --query=sparql/construct-ont-biolink-subclasses.rq --results=ttl >$@

slot-mappings.ttl: biolink-model.ttl biolink-local.ttl
	$(ARQ) -q --data=biolink-model.ttl --data=biolink-local.ttl --query=sparql/construct-slot-mappings.rq --results=ttl >$@

ontologies-merged.ttl: ontologies.ofn ubergraph-axioms.ofn ncbi-gene-classes.ttl protein-subclasses.ttl mesh-chebi-links.ttl uniprot-to-ncbi-rules.ofn reacto-uniprot-rules.ttl biolink-class-hierarchy.ttl ont-biolink-subclasses.ttl slot-mappings.ttl mirror
	$(ROBOT) merge --catalog mirror/catalog-v001.xml --include-annotations true \
	-i $< -i ubergraph-axioms.ofn \
	-i ncbi-gene-classes.ttl \
	-i protein-subclasses.ttl \
	-i mesh-chebi-links.ttl \
	-i uniprot-to-ncbi-rules.ofn \
	-i reacto-uniprot-rules.ttl \
	-i biolink-class-hierarchy.ttl \
	-i ont-biolink-subclasses.ttl \
	-i slot-mappings.ttl \
	remove --axioms 'disjoint' --trim true --preserve-structure false \
	remove --term 'owl:Nothing' --trim true --preserve-structure false \
	remove --term 'http://purl.obolibrary.org/obo/caro#part_of' --term 'http://purl.obolibrary.org/obo/caro#develops_from' --trim true --preserve-structure false \
	reason -r ELK -D debug.ofn -o $@

subclass_closure.ttl: ontologies-merged.ttl sparql/subclass-closure.rq
	$(ARQ) -q --data=$< --query=sparql/subclass-closure.rq --results=ttl --optimize=off >$@

is_defined_by.ttl: ontologies-merged.ttl
	$(ARQ) -q --data=$< --query=sparql/isDefinedBy.rq --results=ttl >$@

properties-nonredundant.ttl: ontologies-merged.ttl
	$(NCIT-UTILS) materialize-property-expressions ontologies-merged.ttl properties-nonredundant.ttl properties-redundant.ttl &&\
	touch properties-redundant.ttl

properties-redundant.ttl: properties-nonredundant.ttl

antonyms_HP.txt:
	curl -L 'https://raw.githubusercontent.com/Phenomics/phenopposites/master/opposites/antonyms_HP.txt' -o $@

opposites.ttl: antonyms_HP.txt
	echo "@prefix HP: <http://purl.obolibrary.org/obo/HP_> ." >$@
	awk 'NR > 2 { print $$1, "<http://purl.obolibrary.org/obo/RO_0002604>", $$2, "."}; NR > 2 { print $$2, "<http://reasoner.renci.org/opposite_of>", $$1, "."; } ' antonyms_HP.txt >>$@

# This includes a hack to workaround JSON-LD context problems with biolink
biolink-model.ttl:
	curl -L 'https://raw.githubusercontent.com/biolink/biolink-model/$(BIOLINK)/biolink-model.ttl' -o $@.tmp
	riot --syntax=turtle --output=ntriples $@.tmp | sed -E 's/<https:\/\/w3id.org\/biolink\/vocab\/([^[:space:]][^[:space:]]*):/<http:\/\/purl.obolibrary.org\/obo\/\1_/g' >$@

# Map of predicates between sources and targets
predicates.tsv: cam-db-reasoned.jnl sparql/predicates.rq
	$(BLAZEGRAPH-RUNNER) select --journal=$< --properties=blazegraph.properties --outformat=tsv sparql/predicates.rq $@
	sed -i -e 's;<https://w3id.org/biolink/vocab/;;g' -e 's;>;;g' -e 's;\t;,;g' $@
	sed -i 1d $@

# Removed dependencies properties-nonredundant.ttl properties-redundant.ttl due to the build time they require
noctua-reactome-ctd-models-ubergraph.jnl: noctua-reactome-ctd-models.jnl ontologies-merged.ttl subclass_closure.ttl is_defined_by.ttl opposites.ttl biolink-model.ttl biolink-local.ttl
	cp $< $@ &&\
	$(BLAZEGRAPH-RUNNER) load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/ontology' ontologies-merged.ttl &&\
	$(BLAZEGRAPH-RUNNER) load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/ontology' opposites.ttl &&\
	$(BLAZEGRAPH-RUNNER) load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/ontology' biolink-model.ttl biolink-local.ttl &&\
	$(BLAZEGRAPH-RUNNER) load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/ontology/closure' subclass_closure.ttl &&\
	$(BLAZEGRAPH-RUNNER) load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/ontology' is_defined_by.ttl #&&\
#	$(BLAZEGRAPH-RUNNER) load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/nonredundant' properties-nonredundant.ttl &&\
#	$(BLAZEGRAPH-RUNNER) load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/redundant' properties-redundant.ttl

