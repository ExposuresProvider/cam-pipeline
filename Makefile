# set JAVA_OPTS=-Xmx64G before running make for blazegraph-runner, ctd-to-owl, ncit-utils
# set ROBOT_JAVA_ARGS=-Xmx64G before running make for robot
# git clone git@github.com:geneontology/noctua-models.git
NOCTUA_MODELS_REPO=../noctua-models
# a copy of the above just checked out to dev branch
NOCTUA_MODELS_DEV_REPO=../noctua-models-dev

all: cam-db-reasoned.jnl

noctua-models.jnl: $(NOCTUA_MODELS_REPO)/models/*.ttl
	cp $< $@ &&\
	blazegraph-runner load --journal=$@ --properties=blazegraph.properties --informat=turtle --use-ontology-graph=true $(patsubst %, "%", $^) &&\
	blazegraph-runner update --journal=$@ --properties=blazegraph.properties sparql/delete-non-production-models.ru

noctua-reactome-models.jnl: noctua-models.jnl $(NOCTUA_MODELS_DEV_REPO)/models/reactome-*.ttl
	cp $< $@ &&\
	blazegraph-runner load --journal=$@ --properties=blazegraph.properties --informat=turtle --use-ontology-graph=true $(patsubst %, "%", $(filter-out $<, $^))

noctua-reactome-ctd-models.jnl: noctua-reactome-models.jnl CTD_chem_gene_ixns_structured.xml
	cp $< $@ &&\
	ctd-to-owl CTD_chem_gene_ixns_structured.xml $@ blazegraph.properties

cam-db-reasoned.jnl: noctua-reactome-ctd-models-ubergraph.jnl
	cp $< $@ &&\
	blazegraph-runner reason --journal=$@ --properties=blazegraph.properties --reasoner=arachne --append-graph-name='#inferred' --ontology='http://reasoner.renci.org/ontology' --source-graphs-query=sparql/find-asserted-models.rq

mirror: ontologies.ofn
	rm -rf $@ &&\
	robot mirror -i $< -d $@ -o $@/catalog-v001.xml

ontologies-merged.ttl: ontologies.ofn mirror
	robot merge --catalog mirror/catalog-v001.xml --include-annotations true -i $< -i ubergraph-axioms.ofn \
	remove --axioms 'disjoint' --trim true --preserve-structure false \
	remove --term 'owl:Nothing' --trim true --preserve-structure false \
	reason -r ELK -D debug.ofn -o $@

subclass_closure.ttl: ontologies-merged.ttl subclass-closure.rq
	robot query -i $< --construct sparql/subclass-closure.rq $@

is_defined_by.ttl: ontologies-merged.ttl
	robot query -i $< --construct sparql/isDefinedBy.rq $@

properties-nonredundant.ttl: ontologies-merged.ttl
	ncit-utils materialize-property-expressions ontologies-merged.ttl properties-nonredundant.ttl properties-redundant.ttl &&\
	touch properties-redundant.ttl

properties-redundant.ttl: properties-nonredundant.ttl

antonyms_HP.txt:
	curl -L 'https://raw.githubusercontent.com/Phenomics/phenopposites/master/opposites/antonyms_HP.txt' -o $@

opposites.ttl: antonyms_HP.txt
	echo "@prefix HP: <http://purl.obolibrary.org/obo/HP_> ." >$@
	awk 'NR > 2 { print $$1, "<http://purl.obolibrary.org/obo/RO_0002604>", $$2, "."}; NR > 2 { print $$2, "<http://reasoner.renci.org/opposite_of>", $$1, "."; } ' antonyms_HP.txt >>$@

biolink-model.ttl:
	curl -L 'https://raw.githubusercontent.com/biolink/biolink-model/master/biolink-model.ttl' -o $@

noctua-reactome-ctd-models-ubergraph.jnl: noctua-reactome-ctd-models.jnl ontologies-merged.ttl subclass_closure.ttl is_defined_by.ttl properties-nonredundant.ttl properties-redundant.ttl opposites.ttl
	rm -f $@ &&\
	blazegraph-runner load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/ontology' ontologies-merged.ttl &&\
	blazegraph-runner load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/ontology' opposites.ttl &&\
	blazegraph-runner load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/ontology' biolink-model.ttl &&\
	blazegraph-runner load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/ontology/closure' subclass_closure.ttl &&\
	blazegraph-runner load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/ontology' is_defined_by.ttl &&\
	blazegraph-runner load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/nonredundant' properties-nonredundant.ttl &&\
	blazegraph-runner load --journal=$@ --properties=blazegraph.properties --informat=turtle --graph='http://reasoner.renci.org/redundant' properties-redundant.ttl