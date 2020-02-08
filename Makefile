# set JAVA_OPTS=-Xmx32G before running make for blazegraph-runner and ctd-to-owl
# git clone git@github.com:geneontology/noctua-models.git
NOCTUA_MODELS_REPO=../noctua-models
# a copy of the above just checked out to dev branch
NOCTUA_MODELS_DEV_REPO=../noctua-models-dev


noctua-models.jnl: ubergraph.jnl $(NOCTUA_MODELS_REPO)/models/*.ttl
	cp $< $@ &&\
	blazegraph-runner load --journal=$@ --informat=turtle --use-ontology-graph=true $(patsubst %, "%", $(filter-out $<, $^)) &&\
	blazegraph-runner update --journal=$@ sparql/delete-non-production-models.ru

noctua-reactome-models.jnl: noctua-models.jnl $(NOCTUA_MODELS_DEV_REPO)/models/reactome-*.ttl
	cp $< $@ &&\
	blazegraph-runner load --journal=$@ --informat=turtle --use-ontology-graph=true $(patsubst %, "%", $(filter-out $<, $^))

noctua-reactome-ctd-models.jnl: noctua-reactome-models.jnl CTD_chem_gene_ixns_structured.xml
	cp $< $@ &&\
	ctd-to-owl CTD_chem_gene_ixns_structured.xml $@ blazegraph.properties

cam-db-reasoned.jnl: noctua-reactome-ctd-models.jnl
	cp $< $@ &&\
	blazegraph-runner reason --journal=$@ --reasoner=whelk --append-graph-name='#inferred' --ontology='http://reasoner.renci.org/ontology' --source-graphs-query=sparql/find-asserted-models.rq
