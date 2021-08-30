PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX lego: <http://geneontology.org/lego/>

DELETE {
  GRAPH ?model {
    ?s ?p ?o .
  }
}
WHERE {
    ?model rdf:type owl:Ontology .
    # A hacky way to choose Noctua model graphs
    ?model lego:modelstate ?modelstate .
    FILTER(?modelstate != "production")
    FILTER NOT EXISTS{
    ?model <http://purl.org/pav/providedBy> ?provider .
    FILTER(?provider != "https://reactome.org")}
    GRAPH ?model {
     ?s ?p ?o .
    }
}
