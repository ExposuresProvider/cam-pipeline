BG_RUNNER=JAVA_OPTS=-Xmx8G blazegraph-runner
# git clone git@github.com:geneontology/noctua-models.git
NOCTUA_MODELS_REPO=../noctua-models
# a copy of the above just checked out to dev branch
NOCTUA_MODELS_DEV_REPO=../noctua-models-dev


ubergraph-noctua-models.jnl: ubergraph.jnl $(NOCTUA_MODELS_REPO)/models/*.ttl
	cp $< $@ &&\
	$(BG_RUNNER) load --journal=$@ --informat=turtle --use-ontology-graph=true $(patsubst %, "%", $(filter-out $<, $^)) &&\
	$(BG_RUNNER) update --journal=$@ sparql/delete-non-production-models.ru

ubergraph-noctua-reactome-models.jnl: ubergraph-noctua-models.jnl $(NOCTUA_MODELS_DEV_REPO)/models/reactome-*.ttl
	cp $< $@ &&\
	$(BG_RUNNER) load --journal=$@ --informat=turtle --use-ontology-graph=true $(patsubst %, "%", $(filter-out $<, $^))

cam-db-reasoned.jnl: ubergraph-noctua-models.jnl
	cp $< $@ &&\
	$(BG_RUNNER) reason --journal=$@ --reasoner=whelk --append-graph-name='#inferred' --ontology='http://reasoner.renci.org/ontology' --source-graphs-query=sparql/find-asserted-models.rq
