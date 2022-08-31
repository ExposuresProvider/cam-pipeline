PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX lego: <http://geneontology.org/lego/>
PREFIX pav: <http://purl.org/pav/>

# This is a temporary fix to https://github.com/ExposuresProvider/cam-pipeline/issues/76 -- a more
# permanent fix would require rewriting the SIGNOR to TTL converter to add provenance information.
# Currently we import the SIGNOR models first, use this SPARQL UPDATE to mark them as imported from
# SIGNOR, and then load the remaining models.

INSERT {
  # pav:importedFrom might be more accurate here, but I think
  # sparql/delete-non-production-models.ru deletes models that
  # don't have a pav:providedBy (which also seems to be what
  # the triplestore largely uses), so let's use that to be
  # consistent.
  ?model pav:providedBy <https://signor.uniroma2.it/> .
} WHERE {
  ?model rdf:type owl:Ontology .
  # When generating SIGNOR models, we set lego:modelstate,
  # so we can use that to ensure we're only modifying models
  # here.
  ?model lego:modelstate ?modelstate
}
